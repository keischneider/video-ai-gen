"""
OpenAI Sora API Client for video generation
Supports Sora 2 and Sora 2 Pro models
"""
import os
import time
import logging
import requests
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class SoraClient:
    """Client for OpenAI Sora video generation API"""

    # Available models and their capabilities
    MODELS = {
        "sora-2": {
            "id": "sora-2",
            "max_duration": 20,
            "max_resolution": "1080p",
            "fps_options": [24, 30],
            "cost_per_second": 0.10,  # Approximate
        },
        "sora-2-pro": {
            "id": "sora-2-pro",
            "max_duration": 90,
            "max_resolution": "4k",
            "fps_options": [24, 30, 60],
            "cost_per_second": 0.50,  # Approximate
        },
    }

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize OpenAI Sora API client

        Args:
            api_key: OpenAI API key (or set OPENAI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required")

        # Import openai
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
        except ImportError:
            raise ImportError("Please install openai>=1.51.0: pip install openai")

        # Get model preference from env
        self.default_model = os.getenv("SORA_MODEL", "sora-2")
        self.default_resolution = os.getenv("SORA_RESOLUTION", "720p")

        # Store jobs for tracking
        self.jobs = {}
        self.job_data = {}

        logger.info(f"Initialized Sora client with model: {self.default_model}")

    def generate_video(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "16:9",
        input_video: Optional[str] = None,
        input_image: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate video using OpenAI Sora API

        Args:
            prompt: Text prompt for video generation (max 500 characters)
            duration: Video duration in seconds (1-20 for sora-2, 1-90 for pro)
            aspect_ratio: Video aspect ratio (16:9, 9:16, 1:1)
            input_video: Optional path to input video (for video-to-video, if supported)
            input_image: Optional path to input image (for image-to-video)
            **kwargs: Additional parameters (model, resolution, style, fps)

        Returns:
            Dictionary with job information
        """
        model_name = kwargs.get("model", self.default_model)
        resolution = kwargs.get("resolution", self.default_resolution)
        style = kwargs.get("style")  # cinematic, documentary, animation
        fps = kwargs.get("fps", 24)

        model_info = self.MODELS.get(model_name)
        if not model_info:
            logger.warning(f"Unknown model {model_name}, using sora-2")
            model_name = "sora-2"
            model_info = self.MODELS["sora-2"]

        # Validate duration
        max_duration = model_info["max_duration"]
        if duration > max_duration:
            logger.warning(f"Duration {duration}s exceeds max {max_duration}s for {model_name}, clamping")
            duration = max_duration

        # Truncate prompt if too long
        if len(prompt) > 500:
            logger.warning(f"Prompt exceeds 500 chars, truncating")
            prompt = prompt[:497] + "..."

        logger.info(f"Generating video with Sora ({model_name})")
        logger.info(f"Prompt: {prompt[:100]}...")
        logger.info(f"Duration: {duration}s, Resolution: {resolution}, Aspect: {aspect_ratio}")

        try:
            start_time = time.time()

            # Build request parameters
            create_params = {
                "model": model_name,
                "prompt": prompt,
            }

            # Add optional parameters if supported
            # Note: Check OpenAI docs for exact parameter names
            if duration:
                create_params["duration"] = duration
            if resolution:
                create_params["resolution"] = resolution
            if style:
                create_params["style"] = style

            # Handle image-to-video if input_image provided
            if input_image:
                logger.info(f"Using image input: {input_image}")
                # Read image and include in request
                if not input_image.startswith("http"):
                    with open(input_image, "rb") as f:
                        import base64
                        image_data = base64.b64encode(f.read()).decode()
                        create_params["image"] = image_data
                else:
                    create_params["image_url"] = input_image

            # Handle video-to-video if input_video provided
            if input_video:
                logger.info(f"Video extension requested - extracting first frame")
                # Sora doesn't natively support video-to-video yet,
                # so extract first frame and use as image input
                frame_path = self._extract_first_frame(input_video)
                with open(frame_path, "rb") as f:
                    import base64
                    image_data = base64.b64encode(f.read()).decode()
                    create_params["image"] = image_data

            # Create video generation request
            logger.info("Sending request to Sora API...")
            video = self.client.videos.create(**create_params)

            # Create job ID
            job_id = f"sora_job_{int(time.time())}"
            video_id = video.id if hasattr(video, 'id') else str(video)

            # Store job info
            job_data = {
                "job_id": job_id,
                "video_id": video_id,
                "status": "PROCESSING",
                "model": model_name,
                "prompt": prompt,
                "duration": duration,
                "aspect_ratio": aspect_ratio,
                "resolution": resolution,
                "created_at": start_time,
            }

            self.jobs[job_id] = video
            self.job_data[job_id] = job_data

            logger.info(f"Video generation started: {job_id}")
            logger.info(f"Video ID: {video_id}")

            return job_data

        except Exception as e:
            logger.error(f"Error generating video: {str(e)}")
            raise

    def _extract_first_frame(self, video_path: str) -> str:
        """Extract first frame from video for image-to-video generation"""
        import tempfile
        try:
            import ffmpeg
        except ImportError:
            raise ImportError("ffmpeg-python required for frame extraction")

        temp_dir = tempfile.gettempdir()
        frame_path = os.path.join(temp_dir, f"sora_frame_{int(time.time())}.jpg")

        try:
            stream = ffmpeg.input(video_path)
            stream = ffmpeg.output(stream, frame_path, vframes=1, format='image2')
            ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)
            logger.info(f"Extracted first frame to: {frame_path}")
            return frame_path
        except Exception as e:
            logger.error(f"Error extracting frame: {e}")
            raise

    def wait_for_completion(
        self,
        job_id: str,
        timeout: int = 600,
        poll_interval: int = 10
    ) -> Dict[str, Any]:
        """
        Wait for video generation to complete by polling

        Args:
            job_id: Job identifier
            timeout: Maximum wait time in seconds
            poll_interval: Polling interval in seconds

        Returns:
            Dictionary with job status and output
        """
        if job_id not in self.job_data:
            raise ValueError(f"Job {job_id} not found")

        job_data = self.job_data[job_id]
        video_id = job_data["video_id"]

        logger.info(f"Waiting for job {job_id} to complete...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                # Poll for status
                video_status = self.client.videos.retrieve(video_id)

                status = video_status.status if hasattr(video_status, 'status') else "unknown"
                logger.info(f"Job {job_id} status: {status} (elapsed: {int(time.time() - start_time)}s)")

                if status == "completed":
                    # Get the video URL
                    video_url = None
                    if hasattr(video_status, 'url'):
                        video_url = video_status.url
                    elif hasattr(video_status, 'video_url'):
                        video_url = video_status.video_url
                    elif hasattr(video_status, 'output'):
                        video_url = video_status.output

                    job_data["status"] = "COMPLETED"
                    job_data["output_url"] = video_url
                    job_data["completed_at"] = time.time()

                    logger.info(f"Job {job_id} completed successfully")
                    return job_data

                elif status == "failed":
                    error_msg = getattr(video_status, 'error', 'Unknown error')
                    raise Exception(f"Video generation failed: {error_msg}")

                elif status in ["queued", "in_progress", "processing"]:
                    time.sleep(poll_interval)
                else:
                    logger.warning(f"Unknown status: {status}")
                    time.sleep(poll_interval)

            except Exception as e:
                if "failed" in str(e).lower():
                    raise
                logger.warning(f"Error polling status: {e}")
                time.sleep(poll_interval)

        raise TimeoutError(f"Video generation timed out after {timeout}s")

    def save_video(self, job_id: str, output_path: str) -> str:
        """
        Save generated video to file

        Args:
            job_id: Job identifier
            output_path: Path where to save the video file

        Returns:
            Path to the saved video file
        """
        logger.info(f"Saving video from job {job_id} to {output_path}")

        if job_id not in self.job_data:
            raise ValueError(f"Job {job_id} not found")

        job_data = self.job_data[job_id]
        output_url = job_data.get("output_url")

        if not output_url:
            raise Exception("No output URL available. Call wait_for_completion first.")

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

            file_size = os.path.getsize(output_path)
            logger.info(f"Video saved to: {output_path} ({file_size / 1024 / 1024:.1f} MB)")
            return output_path

        except Exception as e:
            logger.error(f"Error saving video: {str(e)}")
            raise

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get status of a video generation job"""
        if job_id not in self.job_data:
            raise ValueError(f"Job {job_id} not found")
        return self.job_data[job_id]

    def list_models(self) -> Dict[str, Any]:
        """List available models and their capabilities"""
        return self.MODELS

    def estimate_cost(
        self,
        duration: int = 5,
        model: Optional[str] = None
    ) -> float:
        """Estimate cost for video generation"""
        model_name = model or self.default_model
        model_info = self.MODELS.get(model_name, self.MODELS["sora-2"])
        return duration * model_info["cost_per_second"]
