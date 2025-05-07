# picupapp/storage_backends.py

from storages.backends.gcloud import GoogleCloudStorage
from django.conf import settings

class CustomGoogleCloudStorage(GoogleCloudStorage):
    def __init__(self, *args, **kwargs):
        kwargs['bucket_name'] = settings.GS_BUCKET_NAME
        kwargs['credentials'] = settings.GS_CREDENTIALS
        super().__init__(*args, **kwargs)
