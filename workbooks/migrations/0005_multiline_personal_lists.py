from django.db import migrations


def multiline(apps, schema_editor):
    Block = apps.get_model('workbooks', 'WorkbookBlock')
    Block.objects.filter(page__template__title='МІЙ AI-ЗОШИТ',
        label__in=['Ще моя сильна сторона', 'Ще мені складно']).update(
            block_type='textarea', config={'rows': 4, 'placeholder': 'Кожен пункт — з нового рядка'})


class Migration(migrations.Migration):
    dependencies = [('workbooks', '0004_bonus_page')]
    operations = [migrations.RunPython(multiline, migrations.RunPython.noop)]
