from io import BytesIO

from pypdf import PdfReader

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
        from accounts.models import StudyGroup
        teacher = get_user_model().objects.create_user(username='teacher', is_staff=True)
        group = StudyGroup.objects.create(name='Tests', start_date='2026-09-10', teacher=teacher, template=cls.template)
        group.open_pages.set(cls.template.pages.all())
        cls.user.study_group = group
        cls.user.save()

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

    def test_pdf_contains_saved_answers_and_cyrillic(self):
        workbook = StudentWorkbook.objects.create(student=self.user, template=self.template)
        block = WorkbookBlock.objects.filter(block_type='textarea').first()
        StudentAnswer.objects.create(workbook=workbook, block=block, value='Українська відповідь <текст> & деталі')
        response = self.client.get(reverse('export_pdf'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn('attachment', response['Content-Disposition'])
        reader = PdfReader(BytesIO(response.content))
        text = '\n'.join(page.extract_text() for page in reader.pages)
        self.assertGreaterEqual(len(reader.pages), 12)
        self.assertIn('Українська відповідь <текст> & деталі', text)
        for page in self.template.pages.all():
            self.assertIn(' '.join(page.title.split()), ' '.join(text.split()))
        self.client.logout()
        self.assertEqual(self.client.get(reverse('export_pdf')).status_code, 302)

    def test_pdf_long_table_and_private_answers(self):
        workbook = StudentWorkbook.objects.create(student=self.user, template=self.template)
        block = WorkbookBlock.objects.filter(block_type='table').first()
        column = block.config['columns'][0]
        StudentAnswer.objects.create(workbook=workbook, block=block,
                                     value=[{'_row': 'Lesson', column: 'Довга відповідь ' * 400}])
        other = get_user_model().objects.create_user(username='other')
        other_book = StudentWorkbook.objects.create(student=other, template=self.template)
        StudentAnswer.objects.create(workbook=other_book, block=block, value=[{column: 'PRIVATE ANSWER'}])
        response = self.client.get(reverse('export_pdf'))
        self.assertEqual(response.status_code, 200)
        reader = PdfReader(BytesIO(response.content))
        text = '\n'.join(page.extract_text() for page in reader.pages)
        self.assertIn('Довга відповідь', text)
        self.assertNotIn('PRIVATE ANSWER', text)
        self.assertGreater(len(reader.pages), 12)

    def test_registration_disabled_and_login(self):
        self.client.logout()
        count = get_user_model().objects.count()
        self.assertRedirects(self.client.post(reverse('register'), {'username': 'unexpected'}), reverse('login'))
        self.assertEqual(get_user_model().objects.count(), count)
        self.assertTrue(self.client.login(username='student', password='Test-pass-942!'))

    def test_course_structure_and_repeat_seed_preserves_answers(self):
        from workbooks.course_content import PAGES
        self.assertEqual(list(self.template.pages.values_list('title', flat=True)), [p[0] for p in PAGES])
        self.assertEqual(self.template.pages.count(), 12)
        workbook = StudentWorkbook.objects.create(student=self.user, template=self.template)
        block = self.template.pages.first().blocks.filter(block_type='text').first()
        answer = StudentAnswer.objects.create(workbook=workbook, block=block, value='Збережена відповідь')
        count = WorkbookBlock.objects.count()
        call_command('seed_workbook', verbosity=0)
        answer.refresh_from_db()
        self.assertEqual(answer.value, 'Збережена відповідь')
        self.assertEqual(WorkbookBlock.objects.count(), count)

    def test_dynamic_table_rows_round_trip_and_pdf(self):
        block = WorkbookBlock.objects.filter(page__template=self.template, block_type='table').first()
        url = reverse('page_detail', args=[block.page_id])
        key = f'block_{block.pk}'
        data = {f'{key}_rows_present': '1', f'{key}_row': ['1', '2', '3', '4'],
                f'{key}_3_0': 'Новий рядок'}
        self.client.post(url, data)
        answer = StudentAnswer.objects.get(block=block, workbook__student=self.user)
        self.assertEqual(len(answer.value), 4)
        self.assertContains(self.client.get(url), 'Новий рядок')
        pdf = self.client.get(reverse('export_pdf'))
        text = ''.join(p.extract_text() for p in PdfReader(BytesIO(pdf.content)).pages)
        self.assertIn('Новий рядок', text)
        self.client.post(url, {f'{key}_rows_present': '1', f'{key}_row': ['1'], f'{key}_0_0': 'Залишений'})
        answer.refresh_from_db()
        self.assertEqual(len(answer.value), 1)
        self.client.post(url, {f'{key}_rows_present': '1'})
        answer.refresh_from_db()
        self.assertEqual(answer.value, [])
        response = self.client.get(url)
        block_context = next(b for b in response.context['blocks'] if b.pk == block.pk)
        self.assertEqual(block_context.table_rows, [])

    def test_avatar_upload_and_invalid_file(self):
        import tempfile
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        image = BytesIO()
        Image.new('RGB', (800, 600), 'blue').save(image, format='PNG')
        url = reverse('page_detail', args=[self.template.pages.first().pk])
        with tempfile.TemporaryDirectory() as directory, self.settings(MEDIA_ROOT=directory):
            self.client.post(url, {'avatar': SimpleUploadedFile('photo.png', image.getvalue(), content_type='image/png')})
            self.user.refresh_from_db()
            self.assertTrue(self.user.avatar.name.endswith('.jpg'))
            with Image.open(self.user.avatar.path) as saved:
                self.assertEqual(saved.size, (400, 400))
            self.assertContains(self.client.get(url), self.user.avatar.url)
            original = self.user.avatar.name
            response = self.client.post(url, {'avatar': SimpleUploadedFile('bad.png', b'not an image')}, follow=True)
            self.user.refresh_from_db()
            self.assertEqual(self.user.avatar.name, original)
            self.assertContains(response, 'Не вдалося прочитати фото')

    def test_validation_keeps_all_previous_answers_and_submitted_text(self):
        book = StudentWorkbook.objects.create(student=self.user, template=self.template)
        page = self.template.pages.first()
        required = WorkbookBlock.objects.create(page=page, block_type='text', label='Required', required=True)
        rating = WorkbookBlock.objects.create(page=page, block_type='rating', label='Rating', config={'max': 5})
        answer = StudentAnswer.objects.create(workbook=book, block=required, value='Original')
        url = reverse('page_detail', args=[page.pk])
        response = self.client.post(url, {f'block_{required.pk}': 'Attempt', f'block_{rating.pk}': '99'})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['page_form'].errors)
        self.assertContains(response, 'Attempt')
        answer.refresh_from_db()
        self.assertEqual(answer.value, 'Original')
        self.client.post(url, {f'block_{required.pk}': '', f'block_{rating.pk}': '4'})
        answer.refresh_from_db()
        self.assertEqual(answer.value, 'Original')

    def test_atomic_save_and_activity_timestamp(self):
        from unittest.mock import patch
        from django.utils import timezone
        from datetime import timedelta
        book = StudentWorkbook.objects.create(student=self.user, template=self.template)
        page = self.template.pages.first()
        text = page.blocks.filter(block_type='text').first()
        StudentWorkbook.objects.filter(pk=book.pk).update(updated_at=timezone.now() - timedelta(days=1))
        book.refresh_from_db()
        previous = book.updated_at
        original = StudentAnswer.objects.update_or_create
        calls = 0
        def fail_second(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError('Simulated failure')
            return original(*args, **kwargs)
        with patch.object(StudentAnswer.objects, 'update_or_create', side_effect=fail_second):
            with self.assertRaises(RuntimeError):
                self.client.post(reverse('page_detail', args=[page.pk]), {f'block_{text.pk}': 'New'})
        self.assertFalse(book.answers.exists())
        self.client.post(reverse('page_detail', args=[page.pk]), {f'block_{text.pk}': 'New'})
        book.refresh_from_db()
        self.assertGreater(book.updated_at, previous)

    def test_archive_is_read_only_and_layout_survives_rename(self):
        group = self.user.study_group
        group.is_archived = True
        group.save()
        page = self.template.pages.first()
        url = reverse('page_detail', args=[page.pk])
        self.assertEqual(self.client.get(url).status_code, 200)
        self.assertEqual(self.client.post(url, {}).status_code, 403)
        from .layout import prepare_groups
        blocks = list(page.blocks.all())
        prepare_groups(page, blocks)
        before = [(b.continuation, b.ends_card, b.profile_card) for b in blocks]
        for block in blocks:
            block.label = 'Changed heading'
        page.title = 'Renamed page'
        prepare_groups(page, blocks)
        self.assertEqual(before, [(b.continuation, b.ends_card, b.profile_card) for b in blocks])

    def test_avatar_replacement_cleans_old_file(self):
        import tempfile
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        image = BytesIO()
        Image.new('RGB', (50, 50), 'red').save(image, format='PNG')
        url = reverse('page_detail', args=[self.template.pages.first().pk])
        with tempfile.TemporaryDirectory() as directory, self.settings(MEDIA_ROOT=directory):
            self.client.post(url, {'avatar': SimpleUploadedFile('first.png', image.getvalue())})
            self.user.refresh_from_db()
            from pathlib import Path
            old_path = Path(self.user.avatar.path)
            with self.captureOnCommitCallbacks(execute=True):
                self.client.post(url, {'avatar': SimpleUploadedFile('second.png', image.getvalue())})
            self.user.refresh_from_db()
            self.assertFalse(old_path.exists())
            self.assertTrue(Path(self.user.avatar.path).exists())
