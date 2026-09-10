from contextlib import closing
import hashlib
import json
import os
import sqlite3
import tempfile
import zipfile
from pathlib import Path
from datetime import datetime, timezone
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Consistent SQLite backup with media, encryption key and integrity manifest.'

    def add_arguments(self, parser):
        parser.add_argument('--output')

    def handle(self, *args, **options):
        db = settings.DATABASES['default']
        if db['ENGINE'] != 'django.db.backends.sqlite3':
            raise CommandError('This command supports SQLite. For PostgreSQL use pg_dump and separately back up MEDIA_ROOT and CREDENTIAL_ENCRYPTION_KEY.')
        output = Path(options['output'] or Path(settings.BASE_DIR) / 'backups' / ('backup-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f') + '.zip'))
        output.parent.mkdir(parents=True, exist_ok=True)
        manifest = {}
        with tempfile.TemporaryDirectory() as temp:
            snapshot = Path(temp) / 'db.sqlite3'
            with closing(sqlite3.connect(str(db['NAME']))) as source, closing(sqlite3.connect(snapshot)) as target:
                source.backup(target)
                if target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise CommandError('Database integrity check failed')
            with zipfile.ZipFile(output, 'x', zipfile.ZIP_DEFLATED) as archive:
                def add(name, data):
                    archive.writestr(name, data)
                    manifest[name] = hashlib.sha256(data).hexdigest()
                add('db.sqlite3', snapshot.read_bytes())
                media = Path(settings.MEDIA_ROOT)
                if media.exists():
                    for file in media.rglob('*'):
                        if file.is_file() and not file.is_symlink():
                            add('media/' + file.relative_to(media).as_posix(), file.read_bytes())
                key = os.environ.get('CREDENTIAL_ENCRYPTION_KEY')
                key_path = Path(settings.BASE_DIR) / '.credential-key'
                if key or key_path.exists():
                    add('.credential-key', key.encode() if key else key_path.read_bytes())
                archive.writestr('manifest.json', json.dumps(manifest))
        self.stdout.write(str(output.resolve()))
