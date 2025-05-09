from storages.backends.gcloud import GoogleCloudStorage
from google.oauth2 import service_account
import os

class PublicGoogleCloudStorage(GoogleCloudStorage):
    def __init__(self, *args, **kwargs):
        bucket_name = os.getenv('GS_BUCKET_NAME')
        creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        credentials = None

        if creds_path:
            credentials = service_account.Credentials.from_service_account_file(creds_path)

        super().__init__(*args, bucket_name=bucket_name, credentials=credentials)

    def _save(self, name, content):
        name = super()._save(name, content)
        blob = self.bucket.blob(name)
        blob.acl.save_predefined("publicRead")  # <-- 👈 This makes it publicly accessible
        return name
