# Create GCS Bucket for Video Outputs

The Veo API requires a Google Cloud Storage bucket to save generated videos when they are large (extended videos, longer durations, etc.).

## Bucket Configuration

- **Bucket name**: `veo-videos-480821-output`
- **Location**: `us-central1`
- **Storage class**: Standard
- **Access control**: Uniform (bucket-level)

## Option 1: Create via Google Cloud Console (Recommended)

1. Go to [Google Cloud Console - Storage](https://console.cloud.google.com/storage/browser)
2. Click "CREATE BUCKET"
3. Enter bucket name: `veo-videos-480821-output`
4. Choose location type: "Region"
5. Select location: `us-central1 (Iowa)`
6. Choose storage class: "Standard"
7. Choose access control: "Uniform"
8. Click "CREATE"

## Option 2: Create via gcloud CLI

```bash
gcloud storage buckets create gs://veo-videos-480821-output \
  --project=veo-videos-480821 \
  --location=us-central1 \
  --uniform-bucket-level-access
```

## Grant Service Account Access

After creating the bucket, grant your service account the necessary permissions:

1. Go to the bucket in Cloud Console
2. Click the "PERMISSIONS" tab
3. Click "GRANT ACCESS"
4. Add principal: `kai-728@veo-videos-480821.iam.gserviceaccount.com`
5. Assign role: "Storage Object Admin"
6. Click "SAVE"

## Verify Configuration

After creating the bucket, verify your `.env` file has:

```bash
VEO_OUTPUT_BUCKET=gs://veo-videos-480821-output
```

## How It Works

When you generate videos (especially extended videos), the Veo API will:
1. Generate the video
2. Save it to your GCS bucket at `gs://veo-videos-480821-output/veo_output_<timestamp>.mp4`
3. The VEO-FCP pipeline will automatically download the video from GCS
4. Convert it to ProRes format
5. Save it to your local scene folder

This approach handles large video files that can't be returned directly in the API response.
