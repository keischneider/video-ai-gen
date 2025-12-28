#!/usr/bin/env python3
"""
Create GCS bucket for Veo video outputs
"""
import os
from pathlib import Path
from dotenv import load_dotenv
from google.cloud import storage
from google.oauth2 import service_account

# Load environment variables
PROJECT_ROOT = Path(__file__).parent.parent
load_dotenv(PROJECT_ROOT / ".env")

def create_bucket():
    """Create GCS bucket for video outputs"""

    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    bucket_name = "veo-videos-480821-output"
    location = "us-central1"
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    print(f"Creating GCS bucket: gs://{bucket_name}")
    print(f"Project: {project_id}")
    print(f"Location: {location}")

    # Resolve credentials path
    creds_path = Path(credentials_path)
    if not creds_path.is_absolute():
        creds_path = PROJECT_ROOT / credentials_path

    # Create credentials
    credentials = service_account.Credentials.from_service_account_file(
        str(creds_path)
    )

    # Create storage client
    storage_client = storage.Client(
        project=project_id,
        credentials=credentials
    )

    try:
        # Check if bucket already exists
        bucket = storage_client.lookup_bucket(bucket_name)
        if bucket:
            print(f"✓ Bucket already exists: gs://{bucket_name}")
            return

        # Create bucket
        bucket = storage_client.create_bucket(
            bucket_name,
            location=location
        )

        print(f"✓ Bucket created successfully: gs://{bucket_name}")
        print(f"  Location: {bucket.location}")
        print(f"  Storage class: {bucket.storage_class}")

    except Exception as e:
        print(f"✗ Error creating bucket: {str(e)}")
        raise

if __name__ == "__main__":
    create_bucket()
