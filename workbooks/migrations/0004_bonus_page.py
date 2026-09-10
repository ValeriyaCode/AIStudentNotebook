from django.db import migrations


def add_bonus(apps, schema_editor):
    Template = apps.get_model('workbooks', 'WorkbookTemplate')
    Page = apps.get_model('workbooks', 'WorkbookPage')
    Block = apps.get_model('workbooks', 'WorkbookBlock')
    for template in Template.objects.filter(title='МІЙ AI-ЗОШИТ'):
        page, created = Page.objects.get_or_create(
            template=template, title='БОНУС',
            defaults={'position': 11, 'subtitle': 'Твій наступний крок у програмуванні'},
        )
        if created:
            Block.objects.create(page=page, block_type='static_text', position=0,
                card_key='card-0', label='Продовжуй навчання зі знижкою!')
            Block.objects.create(page=page, block_type='static_text', position=1,
                card_key='card-0', label='Для учасників AI-курсу — знижка на навчання Python або Roblox. Обирай, що тобі цікавіше: писати власні програми чи створювати ігри. Щоб дізнатися розмір знижки та умови навчання, звернися до викладача.')


class Migration(migrations.Migration):
    dependencies = [('workbooks', '0003_populate_card_layout')]
    operations = [migrations.RunPython(add_bonus, migrations.RunPython.noop)]
