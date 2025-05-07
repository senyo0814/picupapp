from storages.backends.gcloud import GoogleCloudStorage
from google.oauth2 import service_account
import os

class CustomGoogleCloudStorage(GoogleCloudStorage):
    def __init__(self, *args, **kwargs):
        # Load bucket name from environment variable
        bucket_name = os.getenv('GS_BUCKET_NAME')

        # Load credentials from the service account file if specified
        credentials = None
        creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if creds_path:
            credentials = service_account.Credentials.from_service_account_file(creds_path)

        # Initialize the GoogleCloudStorage backend with custom bucket and credentials
        super().__init__(*args, **kwargs, bucket_name=bucket_name, credentials=credentials)
