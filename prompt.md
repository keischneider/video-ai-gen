python cli.py generate \
  --scene-id scene_01 \
  --prompt "Кремль горит." \
  --dialogue "Гори пидарас, пидарасина." \
  --skip-lipsync

python cli.py generate \
  --scene-id scene_02 \
  --prompt "The fire spreads across the building" \
  --input-video project/scenes/scene_01/scene_01_veo_prores.mov

python cli.py generate \
  --scene-id scene_03 \
  --prompt "Огромный Ленин падает на купол Кремля" \
  --input-video project/scenes/scene_02/scene_02_veo_prores.mov