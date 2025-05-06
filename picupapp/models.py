from django.db import models
from django.contrib.auth.models import User
from PIL import Image
from .exif_utils import extract_gps_and_datetime
import logging

class PhotoUpload(models.Model):
    image = models.ImageField(upload_to='uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    comment = models.TextField(blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    photo_taken_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.image.name} uploaded by {self.uploaded_by}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        try:
            # Use the EXIF utility function
            lat, lon, photo_date = extract_gps_and_datetime(self.image)

            updated_fields = []

            if lat is not None and lon is not None and (self.latitude is None or self.longitude is None):
                self.latitude = lat
                self.longitude = lon
                updated_fields += ['latitude', 'longitude']

            if photo_date and self.photo_taken_date is None:
                self.photo_taken_date = photo_date
                updated_fields.append('photo_taken_date')

            if updated_fields:
                super().save(update_fields=updated_fields)

        except Exception as e:
            logging.getLogger(__name__).exception(f"EXIF extraction failed: {e}")
