from django.db import models
from django.contrib.auth.models import User
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
from datetime import datetime
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

    
    def get_exif_data(self, image):
        """Extract EXIF data from image."""
        exif_data = {}
        info = image._getexif()
        if not info:
            return exif_data
        for tag, value in info.items():
            decoded = TAGS.get(tag, tag)
            if decoded == "GPSInfo":
                gps_data = {}
                for t in value:
                    sub_decoded = GPSTAGS.get(t, t)
                    gps_data[sub_decoded] = value[t]
                exif_data["GPSInfo"] = gps_data
            elif decoded == "DateTimeOriginal":
                exif_data["DateTimeOriginal"] = value
        return exif_data

    def get_lat_lon(self, exif_data):
        """Convert GPS EXIF to latitude and longitude."""
        gps_info = exif_data.get("GPSInfo")
        if not gps_info:
            return None

        def to_degrees(value):
            d = float(value[0][0]) / value[0][1]
            m = float(value[1][0]) / value[1][1]
            s = float(value[2][0]) / value[2][1]
            return d + m / 60.0 + s / 3600.0

        try:
            lat = to_degrees(gps_info['GPSLatitude'])
            if gps_info.get('GPSLatitudeRef') == 'S':
                lat = -lat
            lon = to_degrees(gps_info['GPSLongitude'])
            if gps_info.get('GPSLongitudeRef') == 'W':
                lon = -lon
            return lat, lon
        except Exception:
            return None

    def get_photo_taken_date(self, exif_data):
        """Convert DateTimeOriginal to Python datetime."""
        date_str = exif_data.get("DateTimeOriginal")
        if date_str:
            try:
                return datetime.strptime(date_str, "%Y:%m:%d %H:%M:%S")
            except ValueError:
                pass
        return None

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        try:
            # Reopen from storage to ensure compatibility on cloud platforms
            img = Image.open(self.image)
            exif_data = self.get_exif_data(img)

            coords = self.get_lat_lon(exif_data)
            photo_date = self.get_photo_taken_date(exif_data)

            updated_fields = []

            if coords and not (self.latitude and self.longitude):
                self.latitude, self.longitude = coords
                updated_fields += ['latitude', 'longitude']

            if photo_date and not self.photo_taken_date:
                self.photo_taken_date = photo_date
                updated_fields.append('photo_taken_date')

            if updated_fields:
                super().save(update_fields=updated_fields)

        except Exception as e:
            logging.getLogger(__name__).exception(f"EXIF extraction failed: {e}")

