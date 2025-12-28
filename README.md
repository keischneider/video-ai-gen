# VEO-FCP: AI Video Generation Pipeline for Final Cut Pro

Complete automated pipeline for generating cinematic videos with dialogue using Google Veo, ElevenLabs TTS, and D-ID lip-sync, optimized for Final Cut Pro workflows.

## Features

- **Google Veo API Integration**: Generate high-quality videos from text prompts
- **Replicate & Sora Support**: Alternative video generation providers (cheaper options)
- **Automatic ProRes Conversion**: Converts all videos to Apple ProRes 422 for seamless FCP import
- **Text-to-Speech**: ElevenLabs integration for natural-sounding dialogue
- **AI Lip-Sync**: D-ID Creative Reality Studio for realistic lip-syncing
- **Video Analysis with Claude**: AI-powered video description and metadata generation
- **Scene Management**: Organized folder structure for multi-scene projects
- **Batch Processing**: Process multiple scenes from JSON config files
- **CLI Interface**: Easy-to-use command-line interface
- **Python API**: Use programmatically in your own scripts

## Workflow

```
Text Prompt → Veo API → Video (MP4)
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
│   │   ├── veo_client.py       # Google Veo API client
│   │   ├── replicate_client.py # Replicate API client (cheap alternative)
│   │   ├── sora_client.py      # OpenAI Sora API client
│   │   ├── tts_client.py       # ElevenLabs TTS client
│   │   ├── lipsync_client.py   # D-ID lip-sync client
│   │   └── claude_client.py    # Claude video analysis client
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
    "provider": "veo",
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
