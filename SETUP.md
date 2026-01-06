# VEO-FCP Setup Guide

## Prerequisites

1. **Python 3.9+** installed on your system
2. **FFmpeg** installed and available in PATH
3. **Google Cloud Account** with Veo API access
4. **ElevenLabs API Key** for text-to-speech
5. **D-ID API Key** for lip-sync

## Installation

### 1. Clone or Download the Repository

```bash
cd /Users/kyrylokravchenko/Movies/veo-fcp
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate  # On Windows
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install FFmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows:**
Download from https://ffmpeg.org/download.html

### 5. Configure API Credentials

Run the setup wizard:

```bash
python cli.py setup
```

Or manually create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
```

Then edit `.env` with your credentials:

```env
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
VEO_LOCATION=us-central1

# ElevenLabs TTS API
ELEVENLABS_API_KEY=your-elevenlabs-api-key
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM

# D-ID Lip Sync API
DID_API_KEY=your-did-api-key

# Project Configuration
PROJECT_ROOT=./project
SCENES_DIR=./project/scenes

# FFmpeg Configuration
FFMPEG_PRORES_PROFILE=2  # 0=Proxy, 1=LT, 2=422, 3=422HQ
```

## Google Cloud Setup

### 1. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Vertex AI API
4. Request access to Veo API (currently in preview)

### 2. Create Service Account

1. Navigate to IAM & Admin > Service Accounts
2. Create a new service account
3. Grant the following roles:
   - Vertex AI User
   - Storage Object Viewer (if using Cloud Storage)
4. Create and download a JSON key file
5. Save the path to this file in your `.env` as `GOOGLE_APPLICATION_CREDENTIALS`

## API Keys

### ElevenLabs

1. Sign up at [ElevenLabs](https://elevenlabs.io/)
2. Get your API key from the profile settings
3. Copy the API key to `ELEVENLABS_API_KEY` in `.env`

### D-ID

1. Sign up at [D-ID](https://www.d-id.com/)
2. Get your API key from the developer dashboard
3. Copy the API key to `DID_API_KEY` in `.env`

## Verify Installation

Test your setup:

```bash
# Check project status
python cli.py status

# List available voices (tests ElevenLabs connection)
python -c "from src.clients.tts_client import TTSClient; client = TTSClient(); print([v.name for v in client.list_voices()[:5]])"
```

## Next Steps

See [USAGE.md](USAGE.md) for usage examples and workflow documentation.