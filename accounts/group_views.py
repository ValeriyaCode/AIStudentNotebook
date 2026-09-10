import secrets
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from .models import User, StudyGroup
from .credentials import encrypt, recover
from .submissions import issue, claim
from django.db.models import Q
from .group_forms import GroupForm, StudentNamesForm
from workbooks.models import StudentWorkbook, WorkbookTemplate


def teacher_groups(user):
    if not user.is_admin_user:
        raise PermissionDenied
    return StudyGroup.objects.all() if user.is_superuser else StudyGroup.objects.filter(teacher=user)


def create_students(group, names):
    credentials = []
    for name in names:
        username = 'student_' + secrets.token_hex(5)
        while User.objects.filter(username=username).exists():
            username = 'student_' + secrets.token_hex(5)
        password = ''.join(secrets.choice('ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789') for _ in range(12))
        user = User.objects.create_user(username=username, password=password, first_name=name, study_group=group)
        user.issued_password = encrypt(password)
        user.save(update_fields=['issued_password'])
        StudentWorkbook.objects.create(student=user, template=group.template)
        credentials.append({'name': name, 'username': username, 'password': password, 'student_id': user.pk})
    return credentials


@login_required
@never_cache
def group_create(request):
    teacher_groups(request.user)
    form = GroupForm(request.POST or None)
    names = StudentNamesForm(request.POST or None)
    template = WorkbookTemplate.objects.filter(is_active=True).first()
    if request.method == 'POST' and form.is_valid() and names.is_valid():
        if not template:
            form.add_error(None, 'Спочатку створіть активний шаблон тетради.')
        else:
            with transaction.atomic():
                receipt, created = claim(request, 'create-group')
                if not created:
                    return redirect('group_credentials', group_id=receipt.group_id) if receipt.group_id else redirect('admin_dashboard')
                group = form.save(commit=False)
                group.teacher = request.user
                group.template = template
                group.save()
                first = template.pages.first()
                if first:
                    group.open_pages.add(first)
                create_students(group, names.cleaned_data['names'])
                receipt.group = group
                receipt.save(update_fields=['group'])
            return redirect('group_credentials', group_id=group.pk)
    return render(request, 'accounts/group_create.html', {'form': form, 'names_form': names, 'submission_token': issue(request.user, 'create-group')})


@login_required
@never_cache
def group_detail(request, group_id):
    group = get_object_or_404(teacher_groups(request.user), pk=group_id)
    form = GroupForm(instance=group)
    names = StudentNamesForm()
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'settings':
            form = GroupForm(request.POST, instance=group)
            if form.is_valid():
                with transaction.atomic():
                    form.save()
                    selected = request.POST.getlist('pages')
                    if any(not value.isdigit() for value in selected):
                        raise PermissionDenied
                    group.open_pages.set(group.template.pages.filter(pk__in=selected))
                messages.success(request, 'Налаштування групи збережено.')
                return redirect('group_detail', group_id=group.pk)
        elif action == 'add':
            names = StudentNamesForm(request.POST)
            if names.is_valid():
                with transaction.atomic():
                    receipt, created = claim(request, f'add-students:{group.pk}')
                    if created:
                        create_students(group, names.cleaned_data['names'])
                        receipt.group = group
                        receipt.save(update_fields=['group'])
                return redirect('group_credentials', group_id=group.pk)
    query = request.GET.get('q', '').strip()
    students = group.students.prefetch_related('workbooks').order_by('first_name', 'username')
    if query:
        students = students.filter(Q(first_name__icontains=query) | Q(last_name__icontains=query) | Q(username__icontains=query))
    return render(request, 'accounts/group_detail.html', {
        'group': group, 'form': form, 'names_form': names,
        'pages': group.template.pages.all(), 'open_ids': set(group.open_pages.values_list('pk', flat=True)),
        'students': students, 'q': query, 'submission_token': issue(request.user, f'add-students:{group.pk}'),
    })


@login_required
@require_POST
@never_cache
def student_action(request, group_id, student_id):
    group = get_object_or_404(teacher_groups(request.user), pk=group_id)
    student = get_object_or_404(User, pk=student_id, study_group=group, role=User.Role.STUDENT, is_staff=False, is_superuser=False)
    action = request.POST.get('action')
    if action == 'delete':
        if request.POST.get('confirm') == 'yes':
            student.delete()
            messages.success(request, 'Учня та його відповіді видалено.')
            return redirect('group_detail', group_id=group.pk)
        return render(request, 'accounts/confirm_delete.html', {'target': student.get_full_name(), 'group': group, 'kind': 'student'})
    if action == 'deactivate':
        student.is_active = False
        student.save(update_fields=['is_active'])
        messages.success(request, 'Вхід учня вимкнено. Відповіді збережено.')
    elif action == 'activate':
        student.is_active = True
        student.save(update_fields=['is_active'])
    elif action == 'reset':
        if request.POST.get('confirm') != 'yes':
            return render(request, 'accounts/confirm_reset.html', {'student': student, 'group': group, 'submission_token': issue(request.user, f'reset:{student.pk}')})
        with transaction.atomic():
            receipt, created = claim(request, f'reset:{student.pk}')
            if created:
                password = secrets.token_urlsafe(9)
                student.set_password(password)
                student.issued_password = encrypt(password)
                student.save(update_fields=['password', 'issued_password'])
                receipt.group = group
                receipt.save(update_fields=['group'])
        return redirect('group_credentials', group_id=group.pk)
    return redirect('group_detail', group_id=group.pk)


@login_required
@never_cache
def group_credentials(request, group_id):
    group = get_object_or_404(teacher_groups(request.user), pk=group_id)
    credentials = [{'name': user.get_full_name(), 'username': user.username,
                    'password': recover(user), 'student_id': user.pk}
                   for user in group.students.order_by('first_name', 'username')]
    return render(request, 'accounts/credentials.html', {'group': group, 'credentials': credentials})


@login_required
@require_POST
def group_action(request, group_id):
    group = get_object_or_404(teacher_groups(request.user), pk=group_id)
    action = request.POST.get('action')
    if action in {'archive', 'restore'}:
        group.is_archived = action == 'archive'
        group.save(update_fields=['is_archived'])
        return redirect('admin_dashboard')
    if action == 'delete':
        if request.POST.get('confirm') != 'yes':
            return render(request, 'accounts/confirm_delete.html', {'target': group.name, 'group': group, 'kind': 'group'})
        with transaction.atomic():
            # Delete only student accounts; any staff memberships are detached.
            group.students.filter(role=User.Role.STUDENT, is_staff=False, is_superuser=False).delete()
            group.delete()
        messages.success(request, 'Групу, її учнів та відповіді видалено.')
    return redirect('admin_dashboard')


@login_required
def student_edit(request, student_id):
    from .group_forms import StudentEditForm
    groups = teacher_groups(request.user)
    students = User.objects.filter(role=User.Role.STUDENT, is_staff=False, is_superuser=False)
    if not request.user.is_superuser:
        students = students.filter(study_group__in=groups)
    student = get_object_or_404(students, pk=student_id)
    choices = groups.filter(Q(is_archived=False) | Q(pk=student.study_group_id))
    form = StudentEditForm(request.POST if request.method == 'POST' else None, groups=choices,
                           initial={'first_name': student.first_name, 'last_name': student.last_name, 'study_group': student.study_group_id})
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            student.first_name = form.cleaned_data['first_name']
            student.last_name = form.cleaned_data['last_name']
            student.study_group = form.cleaned_data['study_group']
            student.save(update_fields=['first_name', 'last_name', 'study_group'])
            StudentWorkbook.objects.get_or_create(student=student, template=student.study_group.template)
        messages.success(request, 'Дані учня оновлено. Попередні відповіді збережено.')
        return redirect('group_detail', group_id=student.study_group_id)
    return render(request, 'accounts/student_edit.html', {'form': form, 'student': student})
