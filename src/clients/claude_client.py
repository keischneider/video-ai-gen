"""
Claude client for video analysis and description generation
"""
import os
import base64
import logging
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, List

logger = logging.getLogger(__name__)

try:
    import anthropic
except ImportError:
    anthropic = None
    logger.warning("anthropic package not installed. Install with: pip install anthropic")


class ClaudeClient:
    """Handles video analysis using Claude's vision capabilities"""

    def __init__(self, api_key: Optional[str] = None, num_frames: int = 8):
        """
        Initialize Claude client

        Args:
            api_key: Anthropic API key (or set ANTHROPIC_API_KEY env var)
            num_frames: Number of frames to extract from video for analysis
        """
        if anthropic is None:
            raise ImportError("anthropic package required. Install with: pip install anthropic")

        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment variables")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.num_frames = num_frames
        self.model = "claude-sonnet-4-20250514"  # Good balance of speed/quality for vision

    def extract_frames(self, video_path: str, num_frames: Optional[int] = None) -> List[str]:
        """
        Extract evenly-spaced frames from video

        Args:
            video_path: Path to video file
            num_frames: Number of frames to extract (defaults to self.num_frames)

        Returns:
            List of paths to extracted frame images
        """
        # Convert to absolute path
        video_path = os.path.abspath(video_path)

        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video not found: {video_path}")

        num_frames = num_frames or self.num_frames
        temp_dir = tempfile.mkdtemp(prefix="claude_frames_")
        frame_paths = []

        try:
            # Get video duration using ffprobe
            result = subprocess.run(
                [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    video_path
                ],
                capture_output=True,
                text=True,
                check=True
            )
            duration = float(result.stdout.strip())

            # Adjust num_frames for very short videos
            if duration < 1:
                num_frames = min(num_frames, 3)

            # Calculate timestamps for evenly-spaced frames (avoid seeking to exact end)
            if num_frames == 1:
                timestamps = [duration / 2]
            else:
                # Leave a small margin at the end to avoid seek issues
                safe_duration = max(0, duration - 0.1)
                timestamps = [safe_duration * i / (num_frames - 1) for i in range(num_frames)]

            # Extract frames at each timestamp
            for i, ts in enumerate(timestamps):
                frame_path = os.path.join(temp_dir, f"frame_{i:03d}.jpg")
                try:
                    subprocess.run(
                        [
                            "ffmpeg", "-y", "-ss", str(ts),
                            "-i", video_path,
                            "-frames:v", "1",
                            "-q:v", "2",  # High quality JPEG
                            frame_path
                        ],
                        capture_output=True,
                        check=True
                    )
                    if os.path.exists(frame_path):
                        frame_paths.append(frame_path)
                except subprocess.CalledProcessError:
                    # Skip frames that fail to extract
                    logger.warning(f"Failed to extract frame at {ts}s, skipping")
                    continue

            logger.info(f"Extracted {len(frame_paths)} frames from {video_path}")
            return frame_paths

        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg error extracting frames: {e.stderr}")
            raise
        except Exception as e:
            logger.error(f"Error extracting frames: {str(e)}")
            raise

    def _encode_image(self, image_path: str) -> tuple[str, str]:
        """
        Encode image to base64 for Claude API

        Args:
            image_path: Path to image file

        Returns:
            Tuple of (base64_data, media_type)
        """
        with open(image_path, "rb") as f:
            data = base64.standard_b64encode(f.read()).decode("utf-8")

        # Determine media type
        suffix = Path(image_path).suffix.lower()
        media_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp"
        }
        media_type = media_types.get(suffix, "image/jpeg")

        return data, media_type

    def analyze_video(
        self,
        video_path: str,
        prompt: Optional[str] = None,
        include_generation_prompt: Optional[str] = None
    ) -> str:
        """
        Analyze video and generate description using Claude

        Args:
            video_path: Path to video file
            prompt: Custom prompt for analysis (optional)
            include_generation_prompt: Original generation prompt for context (optional)

        Returns:
            Video description generated by Claude
        """
        # Extract frames
        frame_paths = self.extract_frames(video_path)

        if not frame_paths:
            raise ValueError("No frames could be extracted from video")

        try:
            # Build message content with frames
            content = []

            # Add context if generation prompt provided
            if include_generation_prompt:
                content.append({
                    "type": "text",
                    "text": f"Original generation prompt: {include_generation_prompt}\n\n"
                })

            # Add all frames
            for i, frame_path in enumerate(frame_paths):
                data, media_type = self._encode_image(frame_path)
                content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": data
                    }
                })

            # Add analysis prompt
            analysis_prompt = prompt or """Analyze these video frames and provide a detailed description including:

1. **Scene Description**: What is happening in the video? Describe the main action, setting, and atmosphere.

2. **Visual Elements**: Describe the key visual elements - colors, lighting, composition, camera movement (if apparent from frames).

3. **Subjects**: Identify and describe any people, animals, objects, or characters in the video.

4. **Mood/Tone**: What emotional tone or mood does the video convey?

5. **Technical Quality**: Comment on the video quality, style (cinematic, documentary, animated, etc.), and any notable production aspects.

Provide a cohesive description that would help someone understand the video's content without watching it. Write in clear, descriptive prose."""

            content.append({
                "type": "text",
                "text": analysis_prompt
            })

            # Call Claude API
            logger.info(f"Analyzing video with {len(frame_paths)} frames using {self.model}")
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                messages=[
                    {"role": "user", "content": content}
                ]
            )

            description = response.content[0].text
            logger.info("Video analysis complete")
            return description

        finally:
            # Cleanup temporary frames
            for frame_path in frame_paths:
                try:
                    os.remove(frame_path)
                except OSError:
                    pass
            try:
                os.rmdir(os.path.dirname(frame_paths[0]))
            except OSError:
                pass

    def generate_short_description(self, video_path: str) -> str:
        """
        Generate a brief one-line description of the video

        Args:
            video_path: Path to video file

        Returns:
            Short description (1-2 sentences)
        """
        return self.analyze_video(
            video_path,
            prompt="Describe this video in 1-2 concise sentences. Focus on the main action and subject."
        )

    def generate_tags(self, video_path: str) -> List[str]:
        """
        Generate searchable tags for the video

        Args:
            video_path: Path to video file

        Returns:
            List of tags/keywords
        """
        response = self.analyze_video(
            video_path,
            prompt="Generate 5-10 relevant tags/keywords for this video. Return only the tags, one per line, no numbering or bullets."
        )
        tags = [tag.strip() for tag in response.strip().split('\n') if tag.strip()]
        return tags
