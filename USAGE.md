# Frequently Used CLI Commands

## Environment Setup

```bash
# Create virtual environment
python3.12 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Deactivate environment
deactivate
```

## Video Generation

```bash
# Generate video
cli.py generate \                                                                      
  --scene-id second-scene --prompt "The background is still, static. Camera stands still. Flowers gently pop in animation on the rocks and flow in the river." --negative-prompt "environment moves. image stratches. camera moves. noise appears" --input-image projects/wan-2.5/bratislava-snow/fourth/4.png --end-image projects/wan-2.5/bratislava-snow/fourth/5.png --project-name wan-2.5/bratislava-snow --analyze --count 1
```

## YouTube Download

```bash
# Download YouTube video
python3 cli.py download-youtube \                                                                           
  --url "https://www.youtube.com/watch?v=OazNfoa5ySI" \
  --scene-id first \
  --audio-only \
  --project-name wan-2.5/flower-cartoon
```

## Text-to-Speech (TTS)

```bash
# Basic TTS
# List available voices
python cli.py tts-multi -e edge-tts -t "x" -o x.mp3 --list-voices
python cli.py tts-multi -e gtts -t "x" -o x.mp3 --list-voices --all
python cli.py tts-multi -e pyttsx3 -t "x" -o x.mp3 --list-voices --all

python cli.py tts-multi -e gtts -t 'Чтоб ты сдохла, тварь... хорошего дня' -o out.mp3 --lang ru
python cli.py tts-multi -e edge-tts -t "Чтоб ты сдохла, тварь... хорошего дня" -o out.mp3 -v ru-RU-SvetlanaNeural 
```

## Video Upscaling (Topaz)

```bash
# Upscale to 1080p at 30fps
python3 cli.py upscale -i input.mp4 -r 1080p -f 30

# Upscale to 4K at 60fps
python3 cli.py upscale -i input.mp4 -r 4k -f 60

python3 cli.py upscale \                                                                                         
  --input projects/wan-2.5/flower-cartoon/shop-7/shop-7_raw.mp4 \  --output output_4k.mp4 \                                                                                                  
  --resolution 4k \
  --fps 60 \
  --estimate
```

## Speech to Video

```bash
# Convert speech/audio to video with image
python cli.py speech-to-video \
  --prompt "A cartoon flower character speaking spooky" \
  --image projects/wan-2.5/flower-cartoon/shop/1.png \
  --audio projects/wan-2.5/flower-cartoon/Untitled.m4a \
  --output talking_flower-1.mp4
```
