"""
YouTube video downloading client using pytubefix with OAuth support
"""
import os
import logging
import subprocess
from pathlib import Path
from typing import Optional
from pytubefix import YouTube
from pytubefix.cli import on_progress

logger = logging.getLogger(__name__)


class YouTubeClient:
    """Client for downloading videos from YouTube using pytubefix"""

    def __init__(self, output_format: str = "mp4", use_oauth: bool = True):
        """
        Initialize YouTube client

        Args:
            output_format: Preferred output format (mp4, webm, etc.)
            use_oauth: Whether to use OAuth for age-restricted videos
        """
        self.output_format = output_format
        self.use_oauth = use_oauth

    def _get_youtube(self, url: str) -> YouTube:
        """Get YouTube object with optional OAuth"""
        return YouTube(
            url,
            on_progress_callback=on_progress,
            use_oauth=self.use_oauth,
            allow_oauth_cache=True
        )

    def get_video_info(self, url: str) -> dict:
        """
        Get video metadata without downloading

        Args:
            url: YouTube URL

        Returns:
            Dictionary with video metadata
        """
        try:
            yt = self._get_youtube(url)

            # Get the best video stream for resolution info
            video_stream = yt.streams.filter(progressive=False, file_extension='mp4').order_by('resolution').desc().first()

            return {
                'id': yt.video_id,
                'title': yt.title,
                'duration': yt.length,
                'description': yt.description,
                'uploader': yt.author,
                'view_count': yt.views,
                'width': video_stream.width if video_stream else None,
                'height': video_stream.height if video_stream else None,
                'fps': video_stream.fps if video_stream else None,
                'thumbnail': yt.thumbnail_url,
            }
        except Exception as e:
            logger.error(f"Error getting video info: {str(e)}")
            raise

    def download_video(
        self,
        url: str,
        output_path: str,
        quality: str = "best",
        max_height: Optional[int] = None,
    ) -> str:
        """
        Download video from YouTube

        Args:
            url: YouTube URL
            output_path: Full path for output file (without extension)
            quality: Quality preset ('best', '1080p', '720p', '480p', 'worst')
            max_height: Maximum video height (e.g., 1080, 720)

        Returns:
            Path to downloaded file
        """
        logger.info(f"Downloading video from YouTube: {url}")

        # Create output directory
        output_dir = os.path.dirname(output_path)
        output_filename = os.path.basename(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        try:
            yt = self._get_youtube(url)

            # Determine target height based on quality
            target_height = max_height
            if not target_height:
                if quality == '1080p':
                    target_height = 1080
                elif quality == '720p':
                    target_height = 720
                elif quality == '480p':
                    target_height = 480
                elif quality == 'worst':
                    target_height = 144

            # Get video stream
            if quality == 'worst':
                video_stream = yt.streams.filter(
                    progressive=False,
                    file_extension='mp4',
                    type='video'
                ).order_by('resolution').asc().first()
            elif target_height:
                video_stream = yt.streams.filter(
                    progressive=False,
                    file_extension='mp4',
                    type='video',
                    res=f"{target_height}p"
                ).first()
                # Fallback to best available if target not found
                if not video_stream:
                    video_stream = yt.streams.filter(
                        progressive=False,
                        file_extension='mp4',
                        type='video'
                    ).order_by('resolution').desc().first()
            else:
                video_stream = yt.streams.filter(
                    progressive=False,
                    file_extension='mp4',
                    type='video'
                ).order_by('resolution').desc().first()

            # Get audio stream
            audio_stream = yt.streams.get_audio_only()

            if not video_stream or not audio_stream:
                raise ValueError("Could not find suitable video/audio streams")

            logger.info(f"Downloading video: {video_stream}")
            logger.info(f"Downloading audio: {audio_stream}")

            # Download video and audio separately
            video_path = video_stream.download(
                output_path=output_dir,
                filename=f"{output_filename}_video.mp4"
            )
            audio_path = audio_stream.download(
                output_path=output_dir,
                filename=f"{output_filename}_audio.webm"
            )

            # Merge with ffmpeg
            final_path = f"{output_path}.{self.output_format}"
            merge_cmd = [
                'ffmpeg', '-y',
                '-i', video_path,
                '-i', audio_path,
                '-c:v', 'copy',
                '-c:a', 'aac',
                final_path
            ]

            logger.info("Merging video and audio...")
            subprocess.run(merge_cmd, check=True, capture_output=True)

            # Clean up temp files
            os.remove(video_path)
            os.remove(audio_path)

            logger.info(f"Downloaded video to {final_path}")
            return final_path

        except Exception as e:
            logger.error(f"Error downloading video: {str(e)}")
            raise

    def download_audio(
        self,
        url: str,
        output_path: str,
        audio_format: str = "wav",
    ) -> str:
        """
        Download only audio from YouTube video

        Args:
            url: YouTube URL
            output_path: Full path for output file (without extension)
            audio_format: Audio format (wav, mp3, m4a, etc.)

        Returns:
            Path to downloaded audio file
        """
        logger.info(f"Downloading audio from YouTube: {url}")

        output_dir = os.path.dirname(output_path)
        output_filename = os.path.basename(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        try:
            yt = self._get_youtube(url)

            # Get best audio stream
            audio_stream = yt.streams.get_audio_only()

            if not audio_stream:
                raise ValueError("Could not find audio stream")

            logger.info(f"Downloading audio: {audio_stream}")

            # Download audio
            temp_path = audio_stream.download(
                output_path=output_dir,
                filename=f"{output_filename}_temp"
            )

            # Convert to desired format with ffmpeg
            final_path = f"{output_path}.{audio_format}"
            convert_cmd = [
                'ffmpeg', '-y',
                '-i', temp_path,
                '-vn',
                final_path
            ]

            if audio_format == 'mp3':
                convert_cmd = [
                    'ffmpeg', '-y',
                    '-i', temp_path,
                    '-vn',
                    '-acodec', 'libmp3lame',
                    '-q:a', '2',
                    final_path
                ]
            elif audio_format == 'wav':
                convert_cmd = [
                    'ffmpeg', '-y',
                    '-i', temp_path,
                    '-vn',
                    '-acodec', 'pcm_s16le',
                    '-ar', '44100',
                    final_path
                ]

            logger.info(f"Converting to {audio_format}...")
            subprocess.run(convert_cmd, check=True, capture_output=True)

            # Clean up temp file
            os.remove(temp_path)

            logger.info(f"Downloaded audio to {final_path}")
            return final_path

        except Exception as e:
            logger.error(f"Error downloading audio: {str(e)}")
            raise
