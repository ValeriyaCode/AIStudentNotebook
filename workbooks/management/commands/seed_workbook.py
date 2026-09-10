from django.core.management.base import BaseCommand
from django.db import transaction
from workbooks.course_content import PAGES
from workbooks.course_layout import block_layout
from workbooks.models import WorkbookBlock, WorkbookPage, WorkbookTemplate


class Command(BaseCommand):
    help = 'Створює та активує AI-зошит із 11 розділів, зберігаючи попередні тетради.'

    @transaction.atomic
    def handle(self, *args, **options):
        template, _ = WorkbookTemplate.objects.get_or_create(
            title='МІЙ AI-ЗОШИТ',
            defaults={'description': '11 кроків до самостійного навчання з AI. Твої інструменти, методи, експерименти та відкриття.', 'is_active': False},
        )
        if not template.pages.exists():
            for p_idx, (title, subtitle, blocks) in enumerate(PAGES):
                page = WorkbookPage.objects.create(template=template, title=title, subtitle=subtitle, position=p_idx)
                for b_idx, (block_type, label, config) in enumerate(blocks):
                    WorkbookBlock.objects.create(page=page, block_type=block_type, label=label, config=config, position=b_idx, **block_layout(p_idx, b_idx, label))
        WorkbookTemplate.objects.exclude(pk=template.pk).update(is_active=False)
        template.is_active = True
        template.save(update_fields=['is_active'])
        self.stdout.write(self.style.SUCCESS(f'Активовано AI-зошит: {template.pages.count()} розділів.'))
