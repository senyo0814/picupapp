from django.core.management.base import BaseCommand
from picupapp.models import PhotoUpload
import os

class Command(BaseCommand):
    help = 'Delete PhotoUpload records whose image files are missing from disk.'

    def handle(self, *args, **options):
        count = 0
        for photo in PhotoUpload.objects.all():
            if not photo.image or not os.path.exists(photo.image.path):
                self.stdout.write(f"❌ Missing: {photo.image.name if photo.image else 'No file'} → Deleting DB record.")
                photo.delete()
                count += 1

        self.stdout.write(self.style.SUCCESS(f"✅ Done. Deleted {count} broken photo entries."))
