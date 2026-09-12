from django.conf import settings
from django.db import models


class WorkbookTemplate(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_active', 'title']

    def __str__(self):
        return self.title


class WorkbookPage(models.Model):
    template = models.ForeignKey(WorkbookTemplate, on_delete=models.CASCADE, related_name='pages')
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=300, blank=True)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['position', 'id']

    def __str__(self):
        return self.title if self.title == 'БОНУС' else f'{self.position + 1}. {self.title}'


class WorkbookBlock(models.Model):
    class Type(models.TextChoices):
        STATIC_TEXT = 'static_text', 'Текст / підказка'
        TEXT = 'text', 'Коротка відповідь'
        TEXTAREA = 'textarea', 'Велика відповідь'
        CHECKBOXES = 'checkboxes', 'Список з галочками'
        SELECT = 'select', 'Випадаючий список'
        RATING = 'rating', 'Оцінка зірочками'
        TABLE = 'table', 'Таблиця'

    page = models.ForeignKey(WorkbookPage, on_delete=models.CASCADE, related_name='blocks')
    block_type = models.CharField(max_length=30, choices=Type.choices)
    label = models.CharField(max_length=300, blank=True)
    help_text = models.CharField(max_length=500, blank=True)
    required = models.BooleanField(default=False)
    position = models.PositiveIntegerField(default=0)
    config = models.JSONField(default=dict, blank=True)
    card_key = models.CharField(max_length=80, blank=True)
    card_style = models.CharField(max_length=20, choices=[('', 'Звичайна'), ('profile', 'Про мене'), ('tool', 'Інструменти')], blank=True)
    half_width = models.BooleanField(default=False)

    class Meta:
        ordering = ['position', 'id']

    def __str__(self):
        return self.label or self.get_block_type_display()


class StudentWorkbook(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='workbooks')
    template = models.ForeignKey(WorkbookTemplate, on_delete=models.PROTECT, related_name='student_workbooks')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['student', 'template'], name='one_workbook_per_student_template')
        ]

    def __str__(self):
        return f'{self.student.get_full_name() or self.student.username} — {self.template.title}'

    def completion(self, pages=None):
        queryset = WorkbookBlock.objects.filter(page__template=self.template).exclude(block_type=WorkbookBlock.Type.STATIC_TEXT)
        if pages is not None:
            queryset = queryset.filter(page__in=pages)
        blocks = list(queryset)
        if not blocks:
            return 0
        values = self.answers.filter(block__in=blocks).values_list('value', flat=True)
        def has_answer(value):
            if isinstance(value, list):
                return any(has_answer(item) for item in value)
            if isinstance(value, dict):
                return any(has_answer(item) for key, item in value.items() if key != '_row')
            return value not in (None, '')

        answered = sum(has_answer(value) for value in values)
        return round(answered * 100 / len(blocks))


class StudentAnswer(models.Model):
    workbook = models.ForeignKey(StudentWorkbook, on_delete=models.CASCADE, related_name='answers')
    block = models.ForeignKey(WorkbookBlock, on_delete=models.CASCADE, related_name='answers')
    value = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['workbook', 'block'], name='one_answer_per_workbook_block')
        ]

    def __str__(self):
        return f'{self.workbook} / {self.block}'
