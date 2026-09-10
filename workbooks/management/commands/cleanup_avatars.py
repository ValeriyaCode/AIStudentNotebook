from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand
from accounts.models import User


class Command(BaseCommand):
    help = 'List orphan avatar files; --delete removes only unreferenced files under MEDIA_ROOT/avatars.'

    def add_arguments(self, parser):
        parser.add_argument('--delete', action='store_true')

    def handle(self, *args, **options):
        root = (Path(settings.MEDIA_ROOT) / 'avatars').resolve()
        if not root.exists():
            return
        used = set(User.objects.exclude(avatar='').values_list('avatar', flat=True))
        for file in root.iterdir():
            if file.is_file() and not file.is_symlink() and file.resolve().parent == root and 'avatars/' + file.name not in used:
                if options['delete']:
                    file.unlink()
                self.stdout.write(('Removed ' if options['delete'] else 'Unused ') + file.name)
