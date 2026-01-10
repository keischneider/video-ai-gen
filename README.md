# VEO-FCP: AI Video Generation Pipeline for Final Cut Pro

Complete automated pipeline for generating cinematic videos with dialogue using Google Veo, ElevenLabs TTS, and D-ID lip-sync, optimized for Final Cut Pro workflows.

## Features

- **Google Veo API Integration**: Generate high-quality videos from text prompts
- **Image-to-Video**: Use an input image as the first frame for video generation
- **Replicate & Sora Support**: Alternative video generation providers (cheaper options)
- **Topaz Labs Video Upscaling**: Upscale videos to 720p, 1080p, or 4K with FPS enhancement (15-60fps)
- **Automatic ProRes Conversion**: Converts all videos to Apple ProRes 422 for seamless FCP import
- **Text-to-Speech**: ElevenLabs integration for natural-sounding dialogue
- **AI Lip-Sync**: D-ID Creative Reality Studio for realistic lip-syncing
- **Video Analysis with Claude**: AI-powered video description and metadata generation
- **YouTube Download**: Download videos from YouTube using yt-dlp for use as input or reference
- **Scene Management**: Organized folder structure for multi-scene projects
- **Batch Processing**: Process multiple scenes from JSON config files
- **CLI Interface**: Easy-to-use command-line interface
- **Python API**: Use programmatically in your own scripts

## Workflow

```
Text Prompt (+ optional Image) → Veo API → Video (MP4)
                                    ↓
                          Download & Convert → ProRes 422
                                    ↓
                            (if dialogue exists)
                                    ↓
                      Text → ElevenLabs TTS → Audio (WAV)
                                    ↓
                  Video + Audio → D-ID Lip-sync → Synced Video
                                    ↓
                      Convert to ProRes 422 → Final Cut Pro Ready
```

## Quick Start

### 1. Installation

```bash
# Clone or navigate to the project
cd veo-fcp

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install FFmpeg (macOS)
brew install ffmpeg
```

### 2. Configure API Keys

```bash
# Run setup wizard
python cli.py setup

# Or manually copy .env.example to .env and edit
cp .env.example .env
```

### 3. Generate Your First Scene

```bash
python cli.py generate \
  --scene-id scene_01 \
  --prompt "A woman walks through a futuristic city at sunset" \
  --dialogue "The city never sleeps, but sometimes I wish it would." \
  --project-name my-film
```

### 4. Import to Final Cut Pro

The final ProRes video will be saved to:
```
projects/my-film/scene_01/scene_01_final_prores.mov
```

Import this file directly into Final Cut Pro!

## Documentation

- [SETUP.md](SETUP.md) - Detailed installation and configuration guide
- [USAGE.md](USAGE.md) - Complete usage documentation and examples
- [examples/](examples/) - Example scene configuration files

## Project Structure

```
veo-fcp/
├── src/
│   ├── clients/
│   │   ├── veo_client.py           # Google Veo API client
│   │   ├── replicate_client.py     # Replicate API client (cheap alternative)
│   │   ├── sora_client.py          # OpenAI Sora API client
│   │   ├── kling_client.py         # Kling AI video generation client
│   │   ├── topaz_upscale_client.py # Topaz Labs video upscaling (via Replicate)
│   │   ├── tts_client.py           # ElevenLabs TTS client
│   │   ├── lipsync_client.py       # D-ID lip-sync client
│   │   ├── claude_client.py        # Claude video analysis client
│   │   └── youtube_client.py       # YouTube download client (yt-dlp)
│   ├── utils/
│   │   ├── video_processor.py  # Video download & ProRes conversion
│   │   └── scene_manager.py    # Scene folder management
│   ├── models/
│   │   └── prompt.py           # Prompt data models
│   └── workflow.py             # Main workflow orchestrator
├── cli.py                      # Command-line interface
├── examples/                   # Example configuration files
└── projects/                   # All projects root directory
    ├── kremlin/                # Example project
    │   ├── scene_01/
    │   └── scene_02/
    └── sveta-running-kherson/  # Another project
        └── scene_01/
```

## CLI Commands

### Generate Single Scene (Full Pipeline)

Generate video with Veo, add TTS dialogue, and apply lip-sync:

```bash
python cli.py generate \
  --scene-id scene_01 \
  --prompt "Your cinematic description" \
  --character "Character details" \
  --camera "Camera movement" \
  --lighting "Lighting style" \
  --emotion "Emotional tone" \
  --dialogue "Spoken dialogue" \
  --input-image /path/to/first_frame.jpg  # Optional: use image as first frame
  --project-name my-film
```

### Generate with Video Analysis

Add `--analyze` to automatically analyze the generated video with Claude and save description to metadata:

```bash
python cli.py generate \
  --scene-id scene_01 \
  --prompt "A woman walks through a futuristic city at sunset" \
  --project-name my-film \
  --analyze
```

This will:
1. Generate the video
2. Convert to ProRes
3. Extract frames and send to Claude for analysis
4. Save AI-generated description to `metadata.json`

### Generate Video Only (No Audio)

Generate video without TTS or lip-sync by omitting the `--dialogue` option:

```bash
python cli.py generate \
  --scene-id scene_01 \
  --prompt "A woman walks through a futuristic city at sunset" \
  --project-name my-film
```

**Use this when:**
- You only need the video footage
- Planning to add audio separately in Final Cut Pro
- Testing video prompts quickly
- Creating B-roll or background footage

### Extend Existing Video

Extend a 1-30 second video with Veo's video-to-video feature:

```bash
# From local file
python cli.py generate \
  --scene-id scene_01_extended \
  --prompt "The camera zooms in on her face as she turns" \
  --input-video projects/my-film/scene_01/scene_01_raw.mp4 \
  --project-name my-film

# From Google Cloud Storage
python cli.py generate \
  --scene-id scene_02 \
  --prompt "The scene transitions to nighttime" \
  --input-video gs://my-bucket/videos/input.mp4 \
  --project-name my-film
```

**Use this when:**
- Creating longer sequences from existing clips
- Adding continuity between scenes
- Extending generated videos with new directions
- Building narrative progression

### Generate Video from Image (First Frame)

Use an image as the starting frame for video generation:

```bash
# Generate video starting from an image
python cli.py generate \
  --scene-id scene_01 \
  --prompt "The woman slowly turns her head and smiles" \
  --input-image /path/to/first_frame.jpg \
  --project-name my-film

# With dialogue
python cli.py generate \
  --scene-id scene_01 \
  --prompt "Camera slowly zooms in on the character" \
  --input-image /path/to/character.png \
  --dialogue "I've been waiting for this moment." \
  --project-name my-film
```

**Use this when:**
- Ensuring visual consistency with existing assets
- Starting from a specific composition or framing
- Using AI-generated images as video starters
- Creating videos that match storyboard frames
- Maintaining character appearance across scenes

**Supported by all providers:**
- Google Veo: Native image-to-video support
- Replicate: Uses Wan i2v models automatically
- OpenAI Sora: Image input support

### Generate Multiple Variations

Generate multiple scenes with the same prompt, automatically incrementing scene IDs:

```bash
# Generate 5 variations: scene_01, scene_02, scene_03, scene_04, scene_05
python cli.py generate \
  --scene-id scene_01 \
  --prompt "A woman walks through a futuristic city at sunset" \
  --project-name my-film \
  --count 5
```

**Scene ID incrementing examples:**
- `scene_01` → `scene_01`, `scene_02`, `scene_03`, ...
- `shot_5` → `shot_5`, `shot_6`, `shot_7`, ...
- `my_scene_001` → `my_scene_001`, `my_scene_002`, `my_scene_003`, ...

**Use this when:**
- Generating multiple takes to pick the best one
- Creating variations of the same scene
- Batch generating content for A/B testing
- Building a library of similar clips

### Generate Video Without Lip-Sync

Skip the lip-sync step (dialogue audio is still generated):

```bash
python cli.py generate \
  --scene-id scene_01 \
  --prompt "A woman walks through a futuristic city at sunset" \
  --dialogue "The city never sleeps, but sometimes I wish it would." \
  --skip-lipsync \
  --project-name my-film
```

**Use this when:**
- You want to manually sync audio in Final Cut Pro
- Testing prompts quickly without waiting for lip-sync
- D-ID API is not configured
- You prefer to handle lip-sync separately

### Generate Text-to-Speech Only

Generate speech audio without video generation:

```bash
python cli.py tts \
  --text "The city never sleeps, but sometimes I wish it would." \
  --output dialogue.wav
```

**With custom voice:**
```bash
python cli.py tts \
  --text "Your dialogue text here" \
  --output my_audio.wav \
  --voice-id BTL5iDLqtiUxgJtpekus
```

**Use this when:**
- You only need voiceover audio files
- Pre-generating dialogue for multiple scenes
- Testing different voices before video generation
- Creating audio-only content

### Batch Process Multiple Scenes
```bash
python cli.py batch --config-file examples/multi_scene_story.json --project-name my-film
```

### Check Project Status
```bash
python cli.py status --project-name my-film
```

### Analyze Video with Claude

Generate AI-powered descriptions for your videos using Claude's vision capabilities:

```bash
# Analyze a scene's video
python cli.py analyze \
  --scene-id scene_01 \
  --project-name my-film

# Include searchable tags
python cli.py analyze \
  --scene-id scene_01 \
  --project-name my-film \
  --include-tags

# Analyze a specific video file
python cli.py analyze \
  --scene-id scene_01 \
  --video-path /path/to/any/video.mp4 \
  --project-name my-film
```

**This generates:**
- Detailed scene description (visual elements, action, mood)
- Short 1-2 sentence summary
- Searchable tags/keywords
- All saved to `metadata.json`

**Use this when:**
- Building searchable video libraries
- Auto-generating alt text for accessibility
- Creating scene summaries for editing workflows
- Documenting generated content

### Upscale Video with Topaz Labs

Upscale videos to higher resolution (720p, 1080p, 4K) and/or higher frame rate (15-120fps) using Topaz Labs AI via Replicate:

**CLI usage:**
```bash
# Basic upscale to 1080p
python cli.py upscale -i input.mp4

# Upscale to 4K at 60fps
python cli.py upscale -i input.mp4 -r 4k -f 60

# With custom output path
python cli.py upscale -i input.mp4 -o output_4k.mp4 -r 4k -f 60

# Show cost estimate before processing
python cli.py upscale -i input.mp4 -r 4k -f 60 --estimate

# Upscale from URL
python cli.py upscale -i "https://example.com/video.mp4" -r 1080p
```

**CLI options:**
| Option | Short | Description |
|--------|-------|-------------|
| `--input` | `-i` | Input video path or URL (required) |
| `--output` | `-o` | Output path (default: `input_upscaled_<resolution>.mp4`) |
| `--resolution` | `-r` | `720p`, `1080p`, or `4k` (default: 1080p) |
| `--fps` | `-f` | Target FPS 15-120 (default: 30) |
| `--estimate` | | Show cost estimate and confirm before processing |

**Python API:**
```python
from src.clients import TopazUpscaleClient

client = TopazUpscaleClient()

# Upscale a video to 4K at 60fps
result = client.upscale_video(
    video_path="input_video.mp4",
    target_resolution="4k",
    target_fps=60
)

# Save the upscaled video
client.save_video(result["job_id"], "output_upscaled.mp4")

# Estimate cost for a 30-second video at 4K/60fps
cost = client.estimate_cost(30, "4k", 60)  # ~$4.48
```

**Pricing (per 5 seconds of output):**
| Resolution | 30fps | 60fps |
|------------|-------|-------|
| 720p | $0.027 | $0.054 |
| 1080p | $0.108 | $0.216 |
| 4K | $0.374 | $0.747 |

**Notes:**
- Local files under 10MB are uploaded automatically via base64 encoding
- For larger files, upload to a public URL first and pass the URL
- Requires `REPLICATE_API_TOKEN` environment variable

**Environment variables:**
```bash
TOPAZ_UPSCALE_RESOLUTION=1080p  # Default target resolution
TOPAZ_UPSCALE_FPS=30            # Default target FPS
```

### Download from YouTube

Download videos from YouTube using yt-dlp for use as input or reference material.

**Prerequisites:** yt-dlp is installed automatically with project dependencies (`pip install -r requirements.txt`).

**Supported URL formats:**
- Standard: `https://www.youtube.com/watch?v=VIDEO_ID`
- Short: `https://youtu.be/VIDEO_ID`
- With timestamp: `https://youtube.com/watch?v=VIDEO_ID&t=30`

```bash
# Basic download
python cli.py download-youtube \
  --url "https://youtube.com/watch?v=VIDEO_ID" \
  --scene-id yt_clip_01 \
  --project-name my-film

# Download at 720p and convert to ProRes for FCP
python cli.py download-youtube \
  --url "https://youtube.com/watch?v=VIDEO_ID" \
  --scene-id reference_01 \
  --quality 720p \
  --to-prores \
  --project-name my-film

# Download with specific max resolution
python cli.py download-youtube \
  --url "https://youtube.com/watch?v=VIDEO_ID" \
  --scene-id hd_clip \
  --max-height 1080 \
  --project-name my-film

# Download only audio (WAV format)
python cli.py download-youtube \
  --url "https://youtube.com/watch?v=VIDEO_ID" \
  --scene-id audio_ref \
  --audio-only \
  --project-name my-film

# Download and analyze with Claude
python cli.py download-youtube \
  --url "https://youtube.com/watch?v=VIDEO_ID" \
  --scene-id analyzed_clip \
  --analyze \
  --project-name my-film

# Full workflow: download, convert to ProRes, and analyze
python cli.py download-youtube \
  --url "https://youtube.com/watch?v=VIDEO_ID" \
  --scene-id final_ref \
  --quality 1080p \
  --to-prores \
  --analyze \
  --project-name my-film
```

**Options:**
| Option | Description |
|--------|-------------|
| `--url` | YouTube video URL (required) |
| `--scene-id` | Scene identifier for organizing the download (required) |
| `--project-name` | Project name for folder organization |
| `--quality` | Video quality preset: `best`, `1080p`, `720p`, `480p`, `worst` |
| `--max-height` | Maximum video height in pixels (e.g., 720, 1080) |
| `--audio-only` | Download only audio in WAV format |
| `--to-prores` | Convert to ProRes 422 after download for FCP compatibility |
| `--analyze` | Analyze video with Claude after download |

**Output files:**
```
projects/my-film/yt_clip_01/
├── yt_clip_01_raw.mp4           # Downloaded video
├── yt_clip_01_prores.mov        # ProRes version (if --to-prores)
├── yt_clip_01_audio.wav         # Audio only (if --audio-only)
└── metadata.json                # Video info + AI analysis (if --analyze)
```

**Use this when:**
- Downloading reference footage for your project
- Getting source material for video extension with Veo
- Extracting audio from YouTube videos for voiceover reference
- Building a clip library with AI-generated descriptions
- Importing YouTube content into Final Cut Pro (use `--to-prores`)

**Python API usage:**
```python
from src.clients.youtube_client import YouTubeClient

client = YouTubeClient()

# Get video info without downloading
info = client.get_video_info("https://youtube.com/watch?v=VIDEO_ID")
print(f"Title: {info['title']}, Duration: {info['duration']}s")

# Download video
video_path = client.download_video(
    url="https://youtube.com/watch?v=VIDEO_ID",
    output_path="./downloads/my_video",
    quality="720p"
)

# Download audio only
audio_path = client.download_audio(
    url="https://youtube.com/watch?v=VIDEO_ID",
    output_path="./downloads/my_audio",
    audio_format="wav"
)
```

### View All Commands
```bash
python cli.py --help
```

## Final Cut Pro Integration

### Inside FCP create:

#### Libraries
- StoryProject.fcpbundle

#### Events
- 01_Scenes
- 02_Audio
- 03_Music
- 04_SFX
- 05_VFX

#### Projects
- Scene_01
- Scene_02
- Scene_03
- Final_Master

### Workflow in FCP:

1. Import ProRes scene clips from `projects/{project-name}/*`
2. Lay in synced dialogue
3. Add background ambience per scene
4. Add sound design
5. Insert transitions or match cuts between scenes
6. Final color correction + grading
7. Export in ProRes 422 or H.264

## Requirements

- Python 3.9+
- FFmpeg
- Google Cloud account with Veo API access
- ElevenLabs API key
- D-ID API key
- Anthropic API key (for video analysis with Claude)

## API Providers

- **Google Veo**: https://cloud.google.com/vertex-ai/docs
- **Replicate**: https://replicate.com/ (cheaper alternative ~$0.05/video)
- **OpenAI Sora**: https://openai.com/sora (medium cost ~$0.50-2.50/video)
- **Kling AI**: https://klingai.com/ (video generation)
- **Topaz Labs**: https://replicate.com/topazlabs/video-upscale (video upscaling via Replicate)
- **ElevenLabs**: https://elevenlabs.io/
- **D-ID**: https://www.d-id.com/
- **Anthropic Claude**: https://anthropic.com/ (video analysis)

## Example Output

After processing, each scene folder contains:

```
scene_01/
├── metadata.json                    # Scene metadata + AI descriptions
├── scene_01_veo_raw.mp4            # Raw Veo output
├── scene_01_veo_prores.mov         # ProRes conversion
├── scene_01_dialogue.wav           # Generated TTS audio
├── scene_01_synced.mp4             # Lip-synced video
└── scene_01_final_prores.mov       # Final FCP-ready file ✓
```

### Metadata Example (with Video Analysis)

```json
{
  "scene_id": "scene_01",
  "status": "completed",
  "generation": {
    "prompt": "A woman walks through a futuristic city...",
    "input_video": null,
    "input_image": "/path/to/first_frame.jpg",
    "provider": "veo",
    "model": "veo-2.0-generate-001",
    "generated_at": "2025-12-28 10:30:00"
  },
  "video_analysis": {
    "description": "The video depicts a woman in modern attire...",
    "short_description": "A woman explores a neon-lit cyberpunk cityscape at dusk.",
    "tags": ["cyberpunk", "woman", "city", "sunset", "futuristic"],
    "analyzed_by": "claude",
    "analyzed_at": "2025-12-28 10:35:00"
  }
}
```

## Advanced Usage

### Python API

```python
from src.workflow import VideoProductionWorkflow
from src.models.prompt import VideoPrompt, SceneConfig

# Create workflow for a specific project
workflow = VideoProductionWorkflow(
    projects_root="./projects",
    project_name="mars-landing"
)

# Define prompt
prompt = VideoPrompt(
    cinematic_description="A spaceship lands on Mars",
    camera_movement="Wide establishing shot",
    lighting_style="Dramatic sunset lighting",
    dialogue_text="We've arrived at our destination."
)

# Process scene
config = SceneConfig(scene_id="scene_mars", prompt=prompt)
result = workflow.process_scene(config)

print(f"Final video: {result['final_prores']}")
# Output: projects/mars-landing/scene_mars/scene_mars_final_prores.mov

# With input image as first frame
result = workflow.process_scene(
    config,
    input_image="/path/to/spaceship_frame.jpg"
)
```

## Troubleshooting

### Common Issues

1. **FFmpeg not found**: Install FFmpeg and ensure it's in your PATH
2. **API authentication errors**: Verify your API keys in `.env`
3. **Quota exceeded**: Check your API plan limits
4. **Video processing timeout**: Increase timeout values for longer videos

See [USAGE.md](USAGE.md) for detailed troubleshooting.

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please open an issue or submit a pull request.

## Support

For questions or issues, please open a GitHub issue.
