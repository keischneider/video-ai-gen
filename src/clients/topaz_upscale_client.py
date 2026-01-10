"""
Topaz Labs Video Upscale Client for Replicate API
Upscales video to higher resolution (720p, 1080p, 4K) and higher FPS (15-60)
"""
import os
import time
import logging
import requests
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class TopazUpscaleClient:
    """Client for Topaz Labs video upscaling via Replicate API"""

    MODEL_ID = "topazlabs/video-upscale"

    # Pricing per 5 seconds of output video (varies by input/output resolution and fps)
    PRICING = {
        "720p_30fps": 0.027,
        "720p_60fps": 0.054,
        "1080p_30fps": 0.108,
        "1080p_60fps": 0.216,
        "4k_30fps": 0.374,
        "4k_60fps": 0.747,
    }

    VALID_RESOLUTIONS = ["720p", "1080p", "4k"]
    FPS_RANGE = (15, 60)

    def __init__(self, api_token: Optional[str] = None):
        """
        Initialize Topaz Upscale client

        Args:
            api_token: Replicate API token (or set REPLICATE_API_TOKEN env var)
        """
        self.api_token = api_token or os.getenv("REPLICATE_API_TOKEN")
        if not self.api_token:
            raise ValueError("REPLICATE_API_TOKEN is required")

        try:
            import replicate
            self.replicate = replicate
        except ImportError:
            raise ImportError("Please install replicate: pip install replicate")

        os.environ["REPLICATE_API_TOKEN"] = self.api_token

        # Default settings from env
        self.default_resolution = os.getenv("TOPAZ_UPSCALE_RESOLUTION", "1080p")
        self.default_fps = int(os.getenv("TOPAZ_UPSCALE_FPS", "30"))

        # Job tracking
        self.jobs = {}
        self.job_data = {}

        logger.info(f"Initialized Topaz Upscale client (default: {self.default_resolution} @ {self.default_fps}fps)")

    def upscale_video(
        self,
        video_path: str,
        target_resolution: str = None,
        target_fps: int = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Upscale a video to higher resolution and/or FPS

        Args:
            video_path: Path to input video file or URL
            target_resolution: Target resolution ("720p", "1080p", "4k")
            target_fps: Target FPS (15-60)
            **kwargs: Additional parameters

        Returns:
            Dictionary with job information and output URL
        """
        resolution = target_resolution or self.default_resolution
        fps = target_fps or self.default_fps

        # Validate resolution
        if resolution not in self.VALID_RESOLUTIONS:
            raise ValueError(f"Invalid resolution: {resolution}. Must be one of {self.VALID_RESOLUTIONS}")

        # Validate FPS
        if not (self.FPS_RANGE[0] <= fps <= self.FPS_RANGE[1]):
            raise ValueError(f"Invalid FPS: {fps}. Must be between {self.FPS_RANGE[0]} and {self.FPS_RANGE[1]}")

        logger.info(f"Upscaling video to {resolution} @ {fps}fps")
        logger.info(f"Input: {video_path}")

        try:
            # Prepare input
            input_params = {
                "target_resolution": resolution,
                "target_fps": fps,
            }

            # Handle video input
            if video_path.startswith("http"):
                input_params["video"] = video_path
            else:
                # Upload local file to Replicate first
                if not os.path.exists(video_path):
                    raise FileNotFoundError(f"Video file not found: {video_path}")

                # Topaz requires a publicly accessible URL - Replicate's internal file API
                # URLs don't work because they require authentication.
                # Use base64 data URL for files under 10MB
                file_size = os.path.getsize(video_path)
                max_size = 10 * 1024 * 1024  # 10MB limit for data URLs

                if file_size > max_size:
                    raise ValueError(
                        f"Video file too large ({file_size / 1024 / 1024:.1f}MB). "
                        f"Topaz upscale only supports local files up to 10MB. "
                        f"Please upload to a public URL and provide the URL instead."
                    )

                logger.info(f"Encoding video as data URL ({file_size / 1024:.1f}KB)...")
                import base64
                with open(video_path, "rb") as f:
                    video_data = base64.b64encode(f.read()).decode()
                    data_url = f"data:video/mp4;base64,{video_data}"
                input_params["video"] = data_url
                logger.info("Video encoded successfully")

            # Run the model
            logger.info("Sending request to Topaz upscale API...")
            start_time = time.time()

            output = self.replicate.run(
                self.MODEL_ID,
                input=input_params
            )

            elapsed = time.time() - start_time
            logger.info(f"Video upscaled in {elapsed:.1f}s")

            # Create job ID
            job_id = f"topaz_upscale_{int(time.time())}"

            # Store result
            job_data = {
                "job_id": job_id,
                "status": "COMPLETED",
                "model": "topaz-video-upscale",
                "input_video": video_path,
                "target_resolution": resolution,
                "target_fps": fps,
                "created_at": start_time,
                "completed_at": time.time(),
                "output_url": str(output) if isinstance(output, str) else output,
                "elapsed_seconds": elapsed,
            }

            self.jobs[job_id] = output
            self.job_data[job_id] = job_data

            logger.info(f"Upscale completed: {job_id}")
            if isinstance(output, str):
                logger.info(f"Output URL: {output}")

            return job_data

        except Exception as e:
            logger.error(f"Error upscaling video: {str(e)}")
            raise

    def save_video(self, job_id: str, output_path: str) -> str:
        """
        Save upscaled video to file

        Args:
            job_id: Job identifier
            output_path: Path where to save the video file

        Returns:
            Path to the saved video file
        """
        logger.info(f"Saving upscaled video from job {job_id} to {output_path}")

        if job_id not in self.job_data:
            raise ValueError(f"Job {job_id} not found")

        job_data = self.job_data[job_id]
        output_url = job_data.get("output_url")

        if not output_url:
            raise Exception("No output URL available for this job")

        try:
            # Create output directory if needed
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

            # Download the video
            logger.info(f"Downloading video from: {output_url}")
            response = requests.get(output_url, stream=True, timeout=300)
            response.raise_for_status()

            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            logger.info(f"Video saved to: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error saving video: {str(e)}")
            raise

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get status of an upscale job"""
        if job_id not in self.job_data:
            raise ValueError(f"Job {job_id} not found")
        return self.job_data[job_id]

    def estimate_cost(
        self,
        video_duration_seconds: float,
        target_resolution: str = "1080p",
        target_fps: int = 30
    ) -> float:
        """
        Estimate cost for upscaling a video

        Args:
            video_duration_seconds: Duration of input video in seconds
            target_resolution: Target resolution
            target_fps: Target FPS

        Returns:
            Estimated cost in USD
        """
        # Pricing is per 5 seconds of output
        fps_key = "60fps" if target_fps > 45 else "30fps"
        price_key = f"{target_resolution}_{fps_key}"

        price_per_5s = self.PRICING.get(price_key, 0.108)  # Default to 1080p_30fps
        cost = (video_duration_seconds / 5) * price_per_5s

        return round(cost, 3)

    def _prepare_video_for_upload(self, video_path: str) -> str:
        """
        Re-mux video to ensure proper container metadata for Topaz.
        Some videos (especially from AI generators) may have incomplete metadata.

        Args:
            video_path: Path to input video

        Returns:
            Path to prepared video (may be same as input or a temp file)
        """
        import tempfile
        import subprocess

        # Check if video needs re-muxing by probing it
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", video_path],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                import json
                info = json.loads(result.stdout)
                format_name = info.get("format", {}).get("format_name", "")
                # If it's already a proper mp4/mov, use it directly
                if "mp4" in format_name or "mov" in format_name or "quicktime" in format_name:
                    logger.info(f"Video format OK: {format_name}")
                    return video_path
        except Exception as e:
            logger.warning(f"Could not probe video: {e}")

        # Re-mux to mp4 with proper metadata
        logger.info("Re-muxing video to ensure proper container metadata...")
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f"topaz_input_{int(time.time())}.mp4")

        try:
            result = subprocess.run(
                [
                    "ffmpeg", "-y", "-i", video_path,
                    "-c", "copy",  # Copy streams without re-encoding
                    "-movflags", "+faststart",  # Optimize for streaming
                    temp_path
                ],
                capture_output=True, text=True, timeout=300
            )
            if result.returncode == 0 and os.path.exists(temp_path):
                logger.info(f"Re-muxed video to: {temp_path}")
                return temp_path
            else:
                logger.warning(f"Re-mux failed: {result.stderr}")
                return video_path
        except Exception as e:
            logger.warning(f"Re-mux error: {e}, using original file")
            return video_path

    @staticmethod
    def get_supported_resolutions() -> list:
        """Get list of supported target resolutions"""
        return TopazUpscaleClient.VALID_RESOLUTIONS

    @staticmethod
    def get_fps_range() -> tuple:
        """Get supported FPS range"""
        return TopazUpscaleClient.FPS_RANGE
