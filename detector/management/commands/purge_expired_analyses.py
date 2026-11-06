from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from detector.models import ImageCheck


class Command(BaseCommand):
    help = 'Preview expired analyses; pass --delete to remove their files and rows.'

    def add_arguments(self, parser):
        parser.add_argument('--delete', action='store_true')

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(hours=settings.ANALYSIS_RETENTION_HOURS)
        expired = ImageCheck.objects.filter(uploaded_at__lte=cutoff)
        if not options['delete']:
            self.stdout.write(f'Dry run: {expired.count()} expired analyses. No data deleted.')
            return
        count = 0
        for record in expired.iterator():
            record.delete_with_image()
            count += 1
        self.stdout.write(f'Deleted {count} expired analyses and their images.')
