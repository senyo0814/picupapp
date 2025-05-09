from django.db import models
from django.contrib.auth.models import User
from PIL import Image
from .exif_utils import extract_gps_and_datetime
import logging
from datetime import datetime
from picupapp.storage_backends import PublicGoogleCloudStorage

from .exif_utils import extract_gps_and_datetime  # already in your imports

def user_directory_path(instance, filename):
    # Try to extract date from image EXIF
    try:
        _, _, photo_date = extract_gps_and_datetime(instance.image)
        if photo_date:
            date_str = photo_date.date().isoformat()
        else:
            date_str = datetime.now().date().isoformat()
    except Exception as e:
        logging.warning(f"[WARN] EXIF extraction failed: {e}")
        date_str = datetime.now().date().isoformat()

    path = f'user_{instance.uploaded_by.id}/{date_str}/{filename}'
    logging.info(f"[DEBUG] Computed upload path: {path}")
    return path

class PhotoUpload(models.Model):
    image = models.ImageField(
        upload_to=user_directory_path,
        storage=PublicGoogleCloudStorage()  # 👈 explicitly set storage backend
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField(blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    photo_taken_date = models.DateTimeField(null=True, blank=True)

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

