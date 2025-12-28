"""
Video processing utilities: download and ProRes conversion
"""
import os
import logging
import requests
import ffmpeg
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class VideoProcessor:
    """Handles video download and format conversion"""

    def __init__(self, prores_profile: int = 2):
        """
        Initialize video processor

        Args:
            prores_profile: ProRes profile (0=Proxy, 1=LT, 2=422, 3=422HQ)
        """
        self.prores_profile = prores_profile

    def download_video(self, url: str, output_path: str) -> str:
        """
        Download video from URL

        Args:
            url: Video URL
            output_path: Path to save downloaded video

        Returns:
            Path to downloaded file
        """
        logger.info(f"Downloading video from {url}")

        try:
            # Create output directory if it doesn't exist
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Download with streaming to handle large files
            response = requests.get(url, stream=True, timeout=300)
            response.raise_for_status()

            # Write to file
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            logger.info(f"Downloaded video to {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error downloading video: {str(e)}")
            raise

    def convert_to_h264(
        self,
        input_path: str,
        output_path: Optional[str] = None
    ) -> str:
        """
        Convert video to H264/MP4 format (required for Veo API input)

        Args:
            input_path: Path to input video
            output_path: Path for output video (optional)

        Returns:
            Path to converted H264 file
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        # Generate output path if not provided
        if output_path is None:
            input_file = Path(input_path)
            output_path = str(input_file.parent / f"{input_file.stem}_h264.mp4")

        logger.info(f"Converting {input_path} to H264/MP4")

        try:
            # Convert to H264 using ffmpeg-python
            stream = ffmpeg.input(input_path)
            stream = ffmpeg.output(
                stream,
                output_path,
                vcodec='libx264',
                preset='medium',
                crf=23,
                pix_fmt='yuv420p',
                acodec='aac',
                audio_bitrate='192k',
                ar='48000',
                ac=2
            )

            # Run conversion
            ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)

            logger.info(f"Converted to H264: {output_path}")
            return output_path

        except ffmpeg.Error as e:
            logger.error(f"FFmpeg error: {e.stderr.decode()}")
            raise
        except Exception as e:
            logger.error(f"Error converting video: {str(e)}")
            raise

    def convert_to_prores(
        self,
        input_path: str,
        output_path: Optional[str] = None
    ) -> str:
        """
        Convert video to Apple ProRes 422 format

        Args:
            input_path: Path to input video
            output_path: Path for output video (optional)

        Returns:
            Path to converted ProRes file
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        # Generate output path if not provided
        if output_path is None:
            input_file = Path(input_path)
            output_path = str(input_file.parent / f"{input_file.stem}_prores.mov")

        logger.info(f"Converting {input_path} to ProRes 422")

        try:
            # Convert to ProRes using ffmpeg-python
            stream = ffmpeg.input(input_path)
            stream = ffmpeg.output(
                stream,
                output_path,
                vcodec='prores_ks',
                profile=self.prores_profile,
                vendor='apl0',
                pix_fmt='yuv422p10le',
                acodec='pcm_s16le',
                ar='48000',
                ac=2
            )

            # Run conversion
            ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)

            logger.info(f"Converted to ProRes: {output_path}")
            return output_path

        except ffmpeg.Error as e:
            logger.error(f"FFmpeg error: {e.stderr.decode()}")
            raise
        except Exception as e:
            logger.error(f"Error converting video: {str(e)}")
            raise

    def get_video_info(self, file_path: str) -> dict:
        """
        Get video information using ffprobe

        Args:
            file_path: Path to video file

        Returns:
            Dictionary with video metadata
        """
        try:
            probe = ffmpeg.probe(file_path)
            video_info = next(
                s for s in probe['streams'] if s['codec_type'] == 'video'
            )
            return {
                'duration': float(probe['format']['duration']),
                'width': int(video_info['width']),
                'height': int(video_info['height']),
                'codec': video_info['codec_name'],
                'fps': eval(video_info['r_frame_rate'])
            }
        except Exception as e:
            logger.error(f"Error getting video info: {str(e)}")
            raise

    def process_video_pipeline(
        self,
        video_url: str,
        scene_dir: str,
        scene_id: str
    ) -> tuple[str, str]:
        """
        Complete pipeline: download and convert to ProRes

        Args:
            video_url: URL of generated video
            scene_dir: Scene directory path
            scene_id: Scene identifier

        Returns:
            Tuple of (raw_video_path, prores_video_path)
        """
        # Create scene directory
        os.makedirs(scene_dir, exist_ok=True)

        # Download video
        raw_path = os.path.join(scene_dir, f"{scene_id}_raw.mp4")
        self.download_video(video_url, raw_path)

        # Convert to ProRes
        prores_path = os.path.join(scene_dir, f"{scene_id}_prores.mov")
        self.convert_to_prores(raw_path, prores_path)

        return raw_path, prores_path
