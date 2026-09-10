from io import BytesIO
from pypdf import PdfReader
from django.test import TestCase
from django.urls import reverse
from django.core.management import call_command
from .models import User, StudyGroup


class GroupTests(TestCase):
    def setUp(self):
        call_command('seed_workbook', verbosity=0)
        self.teacher = User.objects.create_user(username='teacher', password='Strong-test-pass', is_staff=True)
        self.client.force_login(self.teacher)

    def create_group(self):
        token = self.client.get(reverse('group_create')).context['submission_token']
        response = self.client.post(reverse('group_create'), {'name': 'Курс', 'start_date': '2026-09-15', 'names': 'Олена\nМарко', 'submission_token': token}, follow=True)
        self.assertEqual(response.status_code, 200)
        return StudyGroup.objects.get(), response.context['credentials']

    def test_create_add_reset_and_deactivate(self):
        group, credentials = self.create_group()
        self.assertEqual(group.students.count(), 2)
        self.assertEqual(group.open_pages.count(), 1)
        first = credentials[0]
        student = group.students.get(username=first['username'])
        self.assertTrue(student.check_password(first['password']))
        self.assertNotEqual(student.password, first['password'])
        self.assertEqual(student.workbooks.count(), 1)
        token = self.client.get(reverse('group_detail', args=[group.pk])).context['submission_token']
        self.client.post(reverse('group_detail', args=[group.pk]), {'action': 'add', 'names': 'Олена', 'submission_token': token})
        self.assertEqual(group.students.count(), 3)
        url = reverse('student_action', args=[group.pk, student.pk])
        confirm = self.client.post(url, {'action': 'reset'})
        response = self.client.post(url, {'action': 'reset', 'confirm': 'yes', 'submission_token': confirm.context['submission_token']}, follow=True)
        student.refresh_from_db()
        self.assertTrue(student.check_password(next(item['password'] for item in response.context['credentials'] if item['username'] == student.username)))
        self.assertFalse(student.check_password(first['password']))
        self.client.post(url, {'action': 'deactivate'})
        student.refresh_from_db()
        self.assertFalse(student.is_active)
        self.assertEqual(student.workbooks.count(), 1)

    def test_locked_pages_and_pdf_and_opening(self):
        group, credentials = self.create_group()
        student = group.students.first()
        pages = list(group.template.pages.all())
        self.client.force_login(student)
        self.assertContains(self.client.get(reverse('dashboard')), 'aria-disabled="true"', count=11)
        locked = reverse('page_detail', args=[pages[1].pk])
        self.assertEqual(self.client.get(locked).status_code, 403)
        self.assertEqual(self.client.post(locked, {}).status_code, 403)
        pdf = self.client.get(reverse('export_pdf'))
        text = ''.join(p.extract_text() for p in PdfReader(BytesIO(pdf.content)).pages)
        self.assertNotIn(pages[1].title, text)
        self.client.force_login(self.teacher)
        self.client.post(reverse('group_detail', args=[group.pk]), {'action': 'settings', 'name': group.name, 'start_date': '2026-09-15', 'pages': [pages[0].pk, pages[1].pk]})
        self.client.force_login(student)
        self.assertEqual(self.client.get(locked).status_code, 200)

    def test_permissions_and_no_group(self):
        group, _ = self.create_group()
        student = group.students.first()
        other = User.objects.create_user(username='other_teacher', is_staff=True)
        self.client.force_login(other)
        self.assertEqual(self.client.get(reverse('group_detail', args=[group.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('student_action', args=[group.pk, student.pk]), {'action': 'reset'}).status_code, 404)
        self.assertEqual(self.client.get(reverse('admin_student_workbook', args=[student.workbooks.first().pk])).status_code, 403)
        self.client.force_login(student)
        self.assertEqual(self.client.get(reverse('group_create')).status_code, 403)
        student.study_group = None
        student.save()
        self.assertEqual(self.client.get(reverse('page_detail', args=[group.template.pages.first().pk])).status_code, 403)

    def test_credentials_can_be_reopened_only_by_teacher(self):
        group, credentials = self.create_group()
        url = reverse('group_credentials', args=[group.pk])
        response = self.client.get(url)
        self.assertContains(response, credentials[0]['password'])
        self.assertIn('no-store', response['Cache-Control'])
        user = group.students.get(username=credentials[0]['username'])
        self.assertNotIn(credentials[0]['password'], user.issued_password)
        self.client.force_login(user)
        self.assertEqual(self.client.get(url).status_code, 403)
        other = User.objects.create_user(username='outsider', is_staff=True)
        self.client.force_login(other)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_old_password_requires_explicit_reset(self):
        group, credentials = self.create_group()
        student = group.students.first()
        student.issued_password = ''
        student.save()
        old_hash = student.password
        response = self.client.get(reverse('group_credentials', args=[group.pk]))
        self.assertContains(response, 'Новий пароль')
        student.refresh_from_db()
        self.assertEqual(student.password, old_hash)

    def test_archive_restore_and_delete_confirmation(self):
        group, _ = self.create_group()
        student_ids = list(group.students.values_list('pk', flat=True))
        url = reverse('group_action', args=[group.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.post(url, {'action': 'archive'})
        group.refresh_from_db()
        self.assertTrue(group.is_archived)
        self.assertNotContains(self.client.get(reverse('admin_dashboard')), f'href="/accounts/groups/{group.pk}/"')
        self.assertContains(self.client.get(reverse('admin_dashboard') + '?archive=1'), group.name)
        self.client.post(url, {'action': 'restore'})
        group.refresh_from_db()
        self.assertFalse(group.is_archived)
        self.client.post(url, {'action': 'delete'})
        self.assertTrue(StudyGroup.objects.filter(pk=group.pk).exists())
        self.client.post(url, {'action': 'delete', 'confirm': 'yes'})
        self.assertFalse(StudyGroup.objects.filter(pk=group.pk).exists())
        self.assertFalse(User.objects.filter(pk__in=student_ids).exists())
        self.assertTrue(User.objects.filter(pk=self.teacher.pk).exists())

    def test_student_delete_and_teacher_pdf(self):
        group, _ = self.create_group()
        student = group.students.first()
        book = student.workbooks.first()
        url = reverse('admin_student_pdf', args=[book.pk])
        response = self.client.get(url)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertTrue(response.content.startswith(b'%PDF'))
        self.client.force_login(student)
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.teacher)
        delete = reverse('student_action', args=[group.pk, student.pk])
        self.client.post(delete, {'action': 'delete'})
        self.assertTrue(User.objects.filter(pk=student.pk).exists())
        self.client.post(delete, {'action': 'delete', 'confirm': 'yes'})
        self.assertFalse(User.objects.filter(pk=student.pk).exists())
        self.assertEqual(group.students.count(), 1)

    def test_duplicate_submission_does_not_create_accounts_twice(self):
        url = reverse('group_create')
        token = self.client.get(url).context['submission_token']
        data = {'name': 'Once', 'start_date': '2026-09-15', 'names': 'One', 'submission_token': token}
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.assertEqual(self.client.post(url, data).status_code, 302)
        self.assertEqual(StudyGroup.objects.count(), 1)
        group = StudyGroup.objects.get()
        self.assertEqual(group.students.count(), 1)
        url = reverse('group_detail', args=[group.pk])
        token = self.client.get(url).context['submission_token']
        data = {'action': 'add', 'names': 'Two', 'submission_token': token}
        self.client.post(url, data)
        self.client.post(url, data)
        self.assertEqual(group.students.count(), 2)
        self.assertEqual(self.client.post(url, {'action': 'add', 'names': 'No token'}).status_code, 403)

    def test_reset_is_confirmed_and_idempotent(self):
        group, _ = self.create_group()
        student = group.students.first()
        original = student.password
        url = reverse('student_action', args=[group.pk, student.pk])
        confirm = self.client.post(url, {'action': 'reset'})
        student.refresh_from_db()
        self.assertEqual(student.password, original)
        data = {'action': 'reset', 'confirm': 'yes', 'submission_token': confirm.context['submission_token']}
        self.client.post(url, data)
        student.refresh_from_db()
        changed = student.password
        self.assertNotEqual(original, changed)
        self.client.post(url, data)
        student.refresh_from_db()
        self.assertEqual(student.password, changed)

    def test_transfer(self):
        group, _ = self.create_group()
        target = StudyGroup.objects.create(name='Destination', start_date='2026-09-20', teacher=self.teacher, template=group.template)
        student = group.students.first()
        original_book = student.workbooks.first().pk
        url = reverse('student_edit', args=[student.pk])
        response = self.client.post(url, {'first_name': 'Нове', 'last_name': 'Ім’я', 'study_group': target.pk})
        self.assertEqual(response.status_code, 302)
        student.refresh_from_db()
        self.assertEqual(student.study_group_id, target.pk)
        self.assertEqual(student.workbooks.get().pk, original_book)
        self.assertContains(self.client.get(reverse('admin_dashboard')), 'Destination')
        self.assertContains(self.client.get(reverse('group_detail', args=[target.pk])), student.username)
        other_teacher = User.objects.create_user(username='foreign_teacher', is_staff=True)
        other = StudyGroup.objects.create(name='Foreign', start_date='2026-09-20', teacher=other_teacher, template=group.template)
        self.client.post(url, {'first_name': 'Attempt', 'study_group': other.pk})
        student.refresh_from_db()
        self.assertEqual(student.study_group_id, target.pk)
