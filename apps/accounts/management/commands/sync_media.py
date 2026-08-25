from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        'Two-way sync between local MEDIA_ROOT and the configured default_storage (S3). '
        'Uploads local files missing from storage, and downloads storage files missing locally.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be uploaded/downloaded without actually doing it.',
        )
        parser.add_argument(
            '--direction',
            choices=['both', 'upload', 'download'],
            default='both',
            help='Restrict sync to one direction (default: both).',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        direction = options['direction']

        media_root = Path(settings.MEDIA_ROOT)
        if not media_root.exists():
            raise CommandError(f'MEDIA_ROOT not found: {media_root}')

        # --- 1. Collect local files (relative posix paths) ---
        local_files = {p.relative_to(media_root).as_posix() for p in media_root.rglob('*') if p.is_file()}

        # --- 2. Collect remote files (relative posix paths) ---
        self.stdout.write('Listing remote files (this may take a while for large buckets)...')
        remote_files = set(self._walk_storage(default_storage, ''))

        uploaded = skipped_up = failed_up = 0
        downloaded = skipped_down = failed_down = 0

        # --- 3. Upload: local -> remote ---
        if direction in ('both', 'upload'):
            missing_remote = sorted(local_files - remote_files)
            for relative_path in missing_remote:
                file_path = media_root / relative_path
                if dry_run:
                    self.stdout.write(f'[dry-run] would upload: {relative_path}')
                    continue
                try:
                    with open(file_path, 'rb') as f:
                        default_storage.save(relative_path, File(f))
                    self.stdout.write(self.style.SUCCESS(f'uploaded: {relative_path}'))
                    uploaded += 1
                except Exception as exc:
                    self.stderr.write(self.style.ERROR(f'failed upload: {relative_path} ({exc})'))
                    failed_up += 1
            skipped_up = len(local_files) - len(missing_remote)

        # --- 4. Download: remote -> local ---
        if direction in ('both', 'download'):
            missing_local = sorted(remote_files - local_files)
            for relative_path in missing_local:
                file_path = media_root / relative_path
                if dry_run:
                    self.stdout.write(f'[dry-run] would download: {relative_path}')
                    continue
                try:
                    file_path.parent.mkdir(parents=True, exist_ok=True)
                    with default_storage.open(relative_path, 'rb') as remote_f:
                        content = remote_f.read()
                    # نوشتن اتمیک روی دیسک محلی
                    tmp_path = file_path.with_suffix(file_path.suffix + '.tmp')
                    with open(tmp_path, 'wb') as local_f:
                        local_f.write(content)
                    tmp_path.replace(file_path)
                    self.stdout.write(self.style.SUCCESS(f'downloaded: {relative_path}'))
                    downloaded += 1
                except Exception as exc:
                    self.stderr.write(self.style.ERROR(f'failed download: {relative_path} ({exc})'))
                    failed_down += 1
            skipped_down = len(remote_files) - len(missing_local)

        self.stdout.write(
            self.style.SUCCESS(
                f'Sync finished. '
                f'uploaded={uploaded}, skipped_upload={skipped_up}, failed_upload={failed_up}, '
                f'downloaded={downloaded}, skipped_download={skipped_down}, failed_download={failed_down}'
            )
        )

    def _walk_storage(self, storage, path):
        directories, files = storage.listdir(path)

        for filename in files:
            if path:
                yield f'{path}/{filename}'
            else:
                yield filename

        for directory in directories:
            sub_path = f'{path}/{directory}' if path else directory
            yield from self._walk_storage(storage, sub_path)
