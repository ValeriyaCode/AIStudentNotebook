from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import extract_answer_value
from .models import StudentAnswer, StudentWorkbook, WorkbookBlock, WorkbookPage, WorkbookTemplate


def _active_template():
    return WorkbookTemplate.objects.filter(is_active=True).first()


def _get_student_workbook(user):
    template = _active_template()
    if not template:
        return None
    workbook, _ = StudentWorkbook.objects.get_or_create(student=user, template=template)
    return workbook


def _is_admin(user):
    return user.is_authenticated and (user.is_staff or getattr(user, 'role', '') == 'admin')


@login_required
def dashboard(request):
    if _is_admin(request.user):
        return redirect('admin_dashboard')
    workbook = _get_student_workbook(request.user)
    pages = workbook.template.pages.all() if workbook else []
    return render(request, 'workbooks/dashboard.html', {'workbook': workbook, 'pages': pages})


@login_required
def page_detail(request, page_id):
    workbook = _get_student_workbook(request.user)
    if not workbook:
        messages.error(request, 'Адміністратор ще не створив активний шаблон тетради.')
        return redirect('dashboard')

    page = get_object_or_404(WorkbookPage, id=page_id, template=workbook.template)
    blocks = list(page.blocks.all())
    existing = {a.block_id: a.value for a in workbook.answers.filter(block__page=page)}

    if request.method == 'POST':
        for block in blocks:
            if block.block_type == WorkbookBlock.Type.STATIC_TEXT:
                continue
            value = extract_answer_value(block, request.POST)
            StudentAnswer.objects.update_or_create(
                workbook=workbook,
                block=block,
                defaults={'value': value},
            )
        messages.success(request, 'Сторінку збережено.')
        next_page = workbook.template.pages.filter(position__gt=page.position).first()
        if 'save_next' in request.POST and next_page:
            return redirect('page_detail', page_id=next_page.id)
        return redirect('page_detail', page_id=page.id)

    for block in blocks:
        block.current_value = existing.get(block.id, [] if block.block_type in {WorkbookBlock.Type.CHECKBOXES, WorkbookBlock.Type.TABLE} else '')
        if block.block_type == WorkbookBlock.Type.RATING:
            block.rating_values = [str(i) for i in range(1, int((block.config or {}).get('max', 5)) + 1)]
        if block.block_type == WorkbookBlock.Type.TABLE:
            rows = (block.config or {}).get('rows', [])
            cols = (block.config or {}).get('columns', [])
            saved_rows = block.current_value if isinstance(block.current_value, list) else []
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

    page_list = list(workbook.template.pages.all())
    idx = page_list.index(page)
    prev_page = page_list[idx - 1] if idx > 0 else None
    next_page = page_list[idx + 1] if idx < len(page_list) - 1 else None

    return render(request, 'workbooks/page_detail.html', {
        'workbook': workbook,
        'page': page,
        'blocks': blocks,
        'prev_page': prev_page,
        'next_page': next_page,
    })


@login_required
def export_pdf(request):
    workbook = _get_student_workbook(request.user)
    if not workbook:
        return redirect('dashboard')

    pages = workbook.template.pages.prefetch_related('blocks')
    answers = {a.block_id: a.value for a in workbook.answers.select_related('block')}

    try:
        from weasyprint import HTML
    except ImportError:
        messages.error(request, 'PDF-модуль не встановлений. Виконайте: pip install -r requirements.txt')
        return redirect('dashboard')
    except OSError:
        messages.error(request, 'Експорт PDF тимчасово недоступний. Зверніться до адміністратора.')
        return redirect('dashboard')

    html = render(request, 'workbooks/pdf.html', {
        'workbook': workbook,
        'pages': pages,
        'answers': answers,
    }).content.decode('utf-8')
    pdf = HTML(string=html, base_url=request.build_absolute_uri('/')).write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="my-workbook.pdf"'
    return response


@user_passes_test(_is_admin)
def admin_dashboard(request):
    workbooks = StudentWorkbook.objects.select_related('student', 'template').order_by('student__username')
    template = _active_template()
    return render(request, 'workbooks/admin_dashboard.html', {'workbooks': workbooks, 'template': template})


@user_passes_test(_is_admin)
def admin_student_workbook(request, workbook_id):
    workbook = get_object_or_404(StudentWorkbook.objects.select_related('student', 'template'), id=workbook_id)
    pages = workbook.template.pages.prefetch_related('blocks')
    answers = {a.block_id: a.value for a in workbook.answers.select_related('block')}
    return render(request, 'workbooks/admin_student_workbook.html', {
        'workbook': workbook,
        'pages': pages,
        'answers': answers,
    })
