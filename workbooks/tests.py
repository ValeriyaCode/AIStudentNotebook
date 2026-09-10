import sys
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .models import StudentAnswer, StudentWorkbook, WorkbookBlock, WorkbookTemplate


class WorkbookTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_workbook', verbosity=0)
        cls.user = get_user_model().objects.create_user(username='student', password='Test-pass-942!')
        cls.template = WorkbookTemplate.objects.get(is_active=True)

    def setUp(self):
        self.client.force_login(self.user)

    def test_pages_and_save(self):
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 200)
        for page in self.template.pages.all():
            self.assertEqual(self.client.get(reverse('page_detail', args=[page.pk])).status_code, 200)
        block = WorkbookBlock.objects.filter(block_type='textarea').first()
        response = self.client.post(reverse('page_detail', args=[block.page_id]), {f'block_{block.pk}': 'My goal'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(StudentAnswer.objects.get(block=block, workbook__student=self.user).value, 'My goal')

    def test_empty_table_does_not_count_as_completed(self):
        workbook = StudentWorkbook.objects.create(student=self.user, template=self.template)
        block = WorkbookBlock.objects.filter(block_type='table').first()
        answer = StudentAnswer.objects.create(workbook=workbook, block=block, value=[{'_row': 'Lesson', 'Topic': ''}])
        self.assertEqual(workbook.completion(), 0)
        answer.value[0]['Topic'] = 'Django'
        answer.save()
        self.assertGreater(workbook.completion(), 0)

    def test_rating_uses_configured_maximum(self):
        block = WorkbookBlock.objects.filter(block_type='rating').first()
        block.config = {'max': 7}
        block.save()
        response = self.client.get(reverse('page_detail', args=[block.page_id]))
        self.assertContains(response, f'name="block_{block.pk}" value="7"')

    def test_student_cannot_access_admin(self):
        self.assertEqual(self.client.get(reverse('admin_dashboard')).status_code, 302)
        self.user.is_staff = True
        self.user.save()
        self.assertEqual(self.client.get(reverse('admin_dashboard')).status_code, 200)

    def test_missing_pdf_native_library(self):
        class MissingLibrary:
            def __getattr__(self, name):
                raise OSError('Native library missing')

        with patch.dict(sys.modules, {'weasyprint': MissingLibrary()}):
            self.assertRedirects(self.client.get(reverse('export_pdf')), reverse('dashboard'))

    def test_registration_and_login(self):
        self.client.logout()
        response = self.client.post(reverse('register'), {
            'username': 'new_student', 'password1': 'A-good-pass-682!', 'password2': 'A-good-pass-682!',
        })
        self.assertRedirects(response, reverse('dashboard'))
        self.client.post(reverse('logout'))
        self.assertTrue(self.client.login(username='new_student', password='A-good-pass-682!'))
