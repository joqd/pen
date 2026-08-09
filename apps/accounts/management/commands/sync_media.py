from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        'Sync local MEDIA_ROOT files into the configured default_storage (S3). '
        'Files that already exist in storage are skipped; only missing files are uploaded.'
    )

    def handle(self, *args, **options):
        media_root = Path(settings.MEDIA_ROOT)
        if not media_root.exists():
            self.stderr.write(self.style.ERROR(f'MEDIA_ROOT not found: {media_root}'))
            return

        uploaded, skipped, failed = 0, 0, 0

        for file_path in sorted(media_root.rglob('*')):
            if not file_path.is_file():
                continue

            relative_path = file_path.relative_to(media_root).as_posix()

            if default_storage.exists(relative_path):
                skipped += 1
                continue

            try:
                with open(file_path, 'rb') as f:
                    default_storage.save(relative_path, File(f))
                self.stdout.write(self.style.SUCCESS(f'uploaded: {relative_path}'))
                uploaded += 1
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f'failed: {relative_path} ({exc})'))
                failed += 1

        self.stdout.write(self.style.SUCCESS(f'Sync finished. uploaded={uploaded}, skipped={skipped}, failed={failed}'))
