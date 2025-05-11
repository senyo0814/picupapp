from django.db import models
from django.contrib.auth.models import User
from PIL import Image
import logging
from datetime import datetime
from .exif_utils import extract_gps_and_datetime
from picupapp.storage_backends import PublicGoogleCloudStorage

def user_directory_path(instance, filename):
    try:
        _, _, photo_date = extract_gps_and_datetime(instance.image)
        date_str = photo_date.date().isoformat() if photo_date else datetime.now().date().isoformat()
    except Exception as e:
        logging.warning(f"[WARN] EXIF extraction failed: {e}")
        date_str = datetime.now().date().isoformat()

    path = f'user_{instance.uploaded_by.id}/{date_str}/{filename}'
    logging.info(f"[DEBUG] Computed upload path: {path}")
    return path

class PhotoGroup(models.Model):
    name = models.CharField(max_length=100, unique=True)  # <-- add unique=True
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    members = models.ManyToManyField(User, related_name='photo_groups')

    def __str__(self):
        return self.name

class PhotoUpload(models.Model):
    VISIBILITY_CHOICES = [
        ('private', 'Private'),
        ('any', 'Any User'),
        ('group', 'Group'),
    ]

    image = models.ImageField(
        upload_to=user_directory_path,
        storage=PublicGoogleCloudStorage()
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField(blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    photo_taken_date = models.DateTimeField(null=True, blank=True)

    visibility = models.CharField(max_length=10, choices=VISIBILITY_CHOICES, default='private')
    group = models.ForeignKey(PhotoGroup, null=True, blank=True, on_delete=models.SET_NULL, related_name='photos')

    def __str__(self):
        return f"{self.image.name} uploaded by {self.uploaded_by}"

    def save(self, *args, **kwargs):
        is_new = self._state.adding

        if is_new and self.image:
            logging.info(f"[DEBUG] Uploading image to: {self.image.url}")

            try:
                lat, lon, photo_date = extract_gps_and_datetime(self.image)
                if lat is not None:
                    self.latitude = lat
                if lon is not None:
                    self.longitude = lon
                if photo_date:
                    self.photo_taken_date = photo_date
            except Exception as e:
                logging.getLogger(__name__).exception(f"EXIF extraction failed: {e}")

        logging.info(f"[DEBUG] Final image name about to save: {self.image.name}")
        super().save(*args, **kwargs)
