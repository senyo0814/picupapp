from django.db import models
from django.contrib.auth.models import User

class PhotoUpload(models.Model):
    image = models.ImageField(upload_to='uploads/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.image.name} uploaded by {self.uploaded_by}"
