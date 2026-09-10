from contextlib import closing
import hashlib
import json
import sqlite3
import zipfile
from pathlib import Path, PurePosixPath
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Verify and restore a backup into a NEW directory; never overwrite the live database.'

    def add_arguments(self, parser):
        parser.add_argument('backup')
        parser.add_argument('--destination', required=True)

    def handle(self, *args, **options):
        destination = Path(options['destination']).resolve()
        if destination.exists():
            raise CommandError('Destination must not exist. Choose a new directory.')
        with zipfile.ZipFile(options['backup']) as archive:
            manifest = json.loads(archive.read('manifest.json'))
            if 'db.sqlite3' not in manifest:
                raise CommandError('Database missing')
            for name, checksum in manifest.items():
                relative = PurePosixPath(name)
                if relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name:
                    raise CommandError('Unsafe archive path')
                if hashlib.sha256(archive.read(name)).hexdigest() != checksum:
                    raise CommandError('Checksum mismatch: ' + name)
            destination.mkdir(parents=True)
            for name in manifest:
                target = destination / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(name))
        with closing(sqlite3.connect(destination / 'db.sqlite3')) as db:
            if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise CommandError('Restored database integrity check failed')
            if db.execute('PRAGMA foreign_key_check').fetchall():
                raise CommandError('Foreign key check failed')
        self.stdout.write('Verified restore: ' + str(destination))
