from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name='WorkbookTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('description', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ['-is_active', 'title']},
        ),
        migrations.CreateModel(
            name='WorkbookPage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('subtitle', models.CharField(blank=True, max_length=300)),
                ('position', models.PositiveIntegerField(default=0)),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pages', to='workbooks.workbooktemplate')),
            ],
            options={'ordering': ['position', 'id']},
        ),
        migrations.CreateModel(
            name='WorkbookBlock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('block_type', models.CharField(choices=[('static_text', 'Текст / підказка'), ('text', 'Коротка відповідь'), ('textarea', 'Велика відповідь'), ('checkboxes', 'Список з галочками'), ('select', 'Випадаючий список'), ('rating', 'Оцінка зірочками'), ('table', 'Таблиця')], max_length=30)),
                ('label', models.CharField(blank=True, max_length=300)),
                ('help_text', models.CharField(blank=True, max_length=500)),
                ('required', models.BooleanField(default=False)),
                ('position', models.PositiveIntegerField(default=0)),
                ('config', models.JSONField(blank=True, default=dict)),
                ('page', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='blocks', to='workbooks.workbookpage')),
            ],
            options={'ordering': ['position', 'id']},
        ),
        migrations.CreateModel(
            name='StudentWorkbook',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='workbooks', to=settings.AUTH_USER_MODEL)),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='student_workbooks', to='workbooks.workbooktemplate')),
            ],
        ),
        migrations.CreateModel(
            name='StudentAnswer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('value', models.JSONField(blank=True, default=dict)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('block', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='answers', to='workbooks.workbookblock')),
                ('workbook', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='answers', to='workbooks.studentworkbook')),
            ],
        ),
        migrations.AddConstraint(
            model_name='studentworkbook',
            constraint=models.UniqueConstraint(fields=('student', 'template'), name='one_workbook_per_student_template'),
        ),
        migrations.AddConstraint(
            model_name='studentanswer',
            constraint=models.UniqueConstraint(fields=('workbook', 'block'), name='one_answer_per_workbook_block'),
        ),
    ]
