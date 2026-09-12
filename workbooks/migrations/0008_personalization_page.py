from django.db import migrations


def split_page(apps, schema_editor):
    Page = apps.get_model('workbooks', 'WorkbookPage')
    Block = apps.get_model('workbooks', 'WorkbookBlock')
    for first in Page.objects.filter(template__title='МІЙ AI-ЗОШИТ', position=0):
        if Page.objects.filter(template_id=first.template_id, title='Персоналізація').exists():
            continue
        for page in Page.objects.filter(template_id=first.template_id, position__gte=1).order_by('-position'):
            page.position += 1
            page.save(update_fields=['position'])
        new = Page.objects.create(template_id=first.template_id, title='Персоналізація', position=1)
        for index, block in enumerate(Block.objects.filter(page=first, position__gte=15)):
            block.page = new
            block.position = index
            block.card_key = f'card-{index // 2}'
            block.save(update_fields=['page', 'position', 'card_key'])


class Migration(migrations.Migration):
    dependencies = [('workbooks', '0007_custom_learning_preferences')]
    operations = [migrations.RunPython(split_page, migrations.RunPython.noop)]
