from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render

from .forms import extract_answer_value, WorkbookPageForm
from django.db import transaction
from django.utils import timezone
from .models import StudentAnswer, StudentWorkbook, WorkbookBlock, WorkbookPage, WorkbookTemplate


def _active_template():
    return WorkbookTemplate.objects.filter(is_active=True).first()


def _get_student_workbook(user):
    template = user.study_group.template if user.study_group_id else _active_template()
    if not template:
        return None
    workbook, _ = StudentWorkbook.objects.get_or_create(student=user, template=template)
    return workbook


def _is_admin(user):
    return user.is_authenticated and (user.is_staff or getattr(user, 'role', '') == 'admin')


def accessible_pages(user, workbook):
    pages = workbook.template.pages.all()
    if _is_admin(user):
        return pages
    if not user.study_group_id:
        return pages.none()
    return pages.filter(pk__in=user.study_group.open_pages.values('pk'))


@login_required
def dashboard(request):
    if _is_admin(request.user):
        return redirect('admin_dashboard')
    workbook = _get_student_workbook(request.user)
    pages = list(workbook.template.pages.all()) if workbook else []
    allowed = set(accessible_pages(request.user, workbook).values_list('pk', flat=True)) if workbook else set()
    for page in pages:
        page.is_open = page.pk in allowed
    available_progress = workbook.completion(accessible_pages(request.user, workbook)) if workbook else 0
    return render(request, 'workbooks/dashboard.html', {'workbook': workbook, 'pages': pages, 'available_progress': available_progress})


@login_required
def page_detail(request, page_id):
    workbook = _get_student_workbook(request.user)
    if not workbook:
        messages.error(request, 'Адміністратор ще не створив активний шаблон тетради.')
        return redirect('dashboard')

    page = get_object_or_404(WorkbookPage, id=page_id, template=workbook.template)
    if not accessible_pages(request.user, workbook).filter(pk=page.pk).exists():
        raise PermissionDenied('Цей розділ ще не відкритий для вашої групи.')
    blocks = list(page.blocks.all())
    existing = {a.block_id: a.value for a in workbook.answers.filter(block__page=page)}

    read_only = bool(request.user.study_group_id and request.user.study_group.is_archived and not _is_admin(request.user))
    form = WorkbookPageForm(blocks, request.POST if request.method == 'POST' else None)
    if request.method == 'POST':
        if read_only:
            raise PermissionDenied('Архівна група: зошит доступний лише для перегляду.')
        valid = form.is_valid()
        avatar = None
        if 'avatar' in request.FILES:
            from accounts.avatar import prepare_avatar
            from django.core.exceptions import ValidationError
            try:
                avatar = prepare_avatar(request.FILES['avatar'])
            except ValidationError as error:
                form.add_error(None, error.messages[0])
                valid = False
        if valid:
            with transaction.atomic():
                if avatar:
                    request.user.avatar = avatar
                    request.user.save(update_fields=['avatar'])
                for block in blocks:
                    if block.block_type == WorkbookBlock.Type.STATIC_TEXT:
                        continue
                    StudentAnswer.objects.update_or_create(
                        workbook=workbook, block=block,
                        defaults={'value': form.cleaned_data[f'block_{block.pk}']},
                    )
                StudentWorkbook.objects.filter(pk=workbook.pk).update(updated_at=timezone.now())
            messages.success(request, 'Сторінку збережено.')
            next_page = accessible_pages(request.user, workbook).filter(position__gt=page.position).first()
            if 'save_next' in request.POST and next_page:
                return redirect('page_detail', page_id=next_page.id)
            return redirect('page_detail', page_id=page.id)
        # Keep submitted answers on screen; do not replace them with older saved data.
        existing = {block.pk: extract_answer_value(block, request.POST) for block in blocks}

    from .layout import prepare_groups
    prepare_groups(page, blocks)
    for block in blocks:
        block.current_value = existing.get(block.id, [] if block.block_type in {WorkbookBlock.Type.CHECKBOXES, WorkbookBlock.Type.TABLE} else '')
        if block.block_type == WorkbookBlock.Type.RATING:
            block.rating_values = [str(i) for i in range(1, int((block.config or {}).get('max', 5)) + 1)]
        if block.block_type == WorkbookBlock.Type.TABLE:
            rows = (block.config or {}).get('rows', [])
            cols = (block.config or {}).get('columns', [])
            saved_rows = block.current_value if isinstance(block.current_value, list) else []
            if block.id in existing:
                rows = [row.get('_row', str(i + 1)) if isinstance(row, dict) else str(i + 1) for i, row in enumerate(saved_rows)]
            table_rows = []
            for r_idx, row_label in enumerate(rows):
                cells = []
                saved_row = saved_rows[r_idx] if r_idx < len(saved_rows) and isinstance(saved_rows[r_idx], dict) else {}
                for c_idx, col_label in enumerate(cols):
                    cells.append({
                        'name': f'block_{block.id}_{r_idx}_{c_idx}',
                        'value': saved_row.get(col_label, ''),
                    })
                table_rows.append({'label': row_label, 'cells': cells})
            block.table_columns = cols
            block.table_rows = table_rows

    page_list = list(accessible_pages(request.user, workbook))
    idx = page_list.index(page)
    prev_page = page_list[idx - 1] if idx > 0 else None
    next_page = page_list[idx + 1] if idx < len(page_list) - 1 else None

    return render(request, 'workbooks/page_detail.html', {
        'workbook': workbook,
        'page': page,
        'blocks': blocks, 'page_form': form, 'read_only': read_only,
        'has_fields': any(block.block_type != WorkbookBlock.Type.STATIC_TEXT for block in blocks),
        'assignment_art': 'images/design/other/' + ['notebook.png', 'books.png', 'lamp.png', 'headphone.png', 'pens.png', 'laptop.png', 'keyboard.png', 'cup.png', 'mouse.png', 'robot.png', 'cup_victory.png', 'present.png'][page.position % 12],
        'prev_page': prev_page,
        'next_page': next_page,
    })


@login_required
def export_pdf(request):
    workbook = _get_student_workbook(request.user)
    if not workbook:
        return redirect('dashboard')

    from .pdf import build_workbook_pdf

    pdf = build_workbook_pdf(workbook, pages=accessible_pages(request.user, workbook))
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="my-workbook.pdf"'
    return response


@user_passes_test(_is_admin)
def admin_dashboard(request):
    from django.db.models import Count
    from accounts.group_views import teacher_groups
    from accounts.models import User
    archived = request.GET.get('archive') == '1'
    groups = teacher_groups(request.user).filter(is_archived=archived).annotate(student_count=Count('students', distinct=True))
    unassigned = User.objects.none()
    if request.user.is_superuser and not archived:
        unassigned = User.objects.filter(study_group__isnull=True, is_staff=False, is_superuser=False, role='student')
    return render(request, 'workbooks/admin_dashboard.html', {'groups': groups, 'unassigned': unassigned, 'archived': archived})



@user_passes_test(_is_admin)
def admin_student_workbook(request, workbook_id):
    workbook = get_object_or_404(StudentWorkbook.objects.select_related('student', 'template'), id=workbook_id)
    if not request.user.is_superuser and (not workbook.student.study_group_id or workbook.student.study_group.teacher_id != request.user.pk):
        raise PermissionDenied
    pages = workbook.template.pages.prefetch_related('blocks')
    answers = {a.block_id: a.value for a in workbook.answers.select_related('block')}
    return render(request, 'workbooks/admin_student_workbook.html', {
        'workbook': workbook,
        'pages': pages,
        'answers': answers,
    })


@user_passes_test(_is_admin)
def admin_student_pdf(request, workbook_id):
    workbook = get_object_or_404(StudentWorkbook.objects.select_related('student', 'template'), pk=workbook_id)
    if not request.user.is_superuser and (not workbook.student.study_group_id or workbook.student.study_group.teacher_id != request.user.pk):
        raise PermissionDenied
    from .pdf import build_workbook_pdf
    response = HttpResponse(build_workbook_pdf(workbook), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="workbook-{workbook.pk}.pdf"'
    return response


@user_passes_test(_is_admin)
def teacher_settings(request):
    return render(request, 'accounts/settings.html')
