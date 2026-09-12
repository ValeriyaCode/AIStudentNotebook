from django.db import migrations


def add_custom_options(apps, schema_editor):
    Block = apps.get_model('workbooks', 'WorkbookBlock')
    for parent in Block.objects.filter(
        page__template__title='МІЙ AI-ЗОШИТ', page__position=0,
        label='Як мені легше сприймати інформацію?',
    ):
        Block.objects.get_or_create(
            page_id=parent.page_id, label='Додай свої варіанти',
            defaults={'block_type': 'textarea', 'position': parent.position + 1,
                      'card_key': parent.card_key,
                      'config': {'rows': 4, 'placeholder': 'Кожен варіант — з нового рядка'}},
        )


class Migration(migrations.Migration):
    dependencies = [('workbooks', '0006_first_experiment_and_personalization')]
    operations = [migrations.RunPython(add_custom_options, migrations.RunPython.noop)]
