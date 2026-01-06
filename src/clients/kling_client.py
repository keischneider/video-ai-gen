"""
Kling AI API Client for video generation
Official API: https://app.klingai.com
Supports text-to-video and image-to-video generation
"""
import os
import time
import logging
import jwt
import requests
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class KlingClient:
    """Client for Kling AI video generation API"""

    BASE_URL = "https://api.klingai.com"

    # Available models
    MODELS = {
        "kling-v1": {"name": "kling-v1", "max_duration": 5},
        "kling-v1-5": {"name": "kling-v1-5", "max_duration": 10},
        "kling-v1-6": {"name": "kling-v1-6", "max_duration": 10},
        "kling-v2": {"name": "kling-v2", "max_duration": 10},
        "kling-v2-1": {"name": "kling-v2-1", "max_duration": 10},
    }

    # Mode options
    MODES = ["std", "pro"]  # standard or professional quality

    def __init__(
        self,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None
    ):
        """
        Initialize Kling AI API client

        Args:
            access_key: Kling API Access Key (or set KLING_ACCESS_KEY env var)
            secret_key: Kling API Secret Key (or set KLING_SECRET_KEY env var)
        """
        self.access_key = access_key or os.getenv("KLING_ACCESS_KEY")
        self.secret_key = secret_key or os.getenv("KLING_SECRET_KEY")

        if not self.access_key or not self.secret_key:
            raise ValueError(
                "KLING_ACCESS_KEY and KLING_SECRET_KEY are required. "
                "Get them from https://app.klingai.com/global/dev/api-key"
            )

        # Default settings from env
        self.default_model = os.getenv("KLING_MODEL", "kling-v1-6")
        self.default_mode = os.getenv("KLING_MODE", "std")

        # Store jobs for tracking
        self.jobs = {}
        self.job_data = {}

        # JWT token cache
        self._token = None
        self._token_expires_at = 0

        logger.info(f"Initialized Kling client with model: {self.default_model}")

    def _generate_jwt_token(self) -> str:
        """
        Generate JWT token for API authentication

        Returns:
            JWT token string
        """
        now = int(time.time())

        # Check if cached token is still valid (with 60s buffer)
        if self._token and self._token_expires_at > now + 60:
            return self._token

        # Token expires in 30 minutes
        exp_time = now + 1800

        payload = {
            "iss": self.access_key,
            "exp": exp_time,
            "nbf": now - 5  # Valid from 5 seconds ago (clock skew buffer)
        }

        headers = {
            "alg": "HS256",
            "typ": "JWT"
        }

        token = jwt.encode(payload, self.secret_key, algorithm="HS256", headers=headers)

        # Cache the token
        self._token = token
        self._token_expires_at = exp_time

        return token

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication"""
        return {
            "Authorization": f"Bearer {self._generate_jwt_token()}",
            "Content-Type": "application/json"
        }

    def _upload_image(self, image_path: str) -> str:
        """
        Upload local image and get base64 string for API use

        Args:
            image_path: Path to local image file

        Returns:
            Raw base64 encoded image string (no data URI prefix)
        """
        import base64

        with open(image_path, "rb") as f:
            image_data = f.read()

        # Kling expects raw base64 string, not data URI
        base64_data = base64.b64encode(image_data).decode("utf-8")
        return base64_data

    def generate_video(
        self,
        prompt: str,
        duration: int = 5,
        aspect_ratio: str = "16:9",
        input_video: Optional[str] = None,
        input_image: Optional[str] = None,
        end_image: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate video using Kling AI API

        Args:
            prompt: Text prompt for video generation
            duration: Video duration in seconds (5 or 10)
            aspect_ratio: Video aspect ratio (16:9, 9:16, 1:1)
            input_video: Optional path/URL to input video for extension
            input_image: Optional path/URL to input image for image-to-video
            end_image: Optional path/URL to end image for interpolation (requires pro mode)
            **kwargs: Additional parameters:
                - model: Model name (default: kling-v1-6)
                - mode: Quality mode 'std' or 'pro' (default: std)
                - cfg_scale: Prompt adherence 0-1 (default: 0.5)
                - negative_prompt: What to avoid in generation
                - camera_control: Camera movement settings

        Returns:
            Dictionary with job information
        """
        model = kwargs.get("model", self.default_model)
        mode = kwargs.get("mode", self.default_mode)

        # Determine endpoint and prepare payload
        if input_image:
            endpoint = f"{self.BASE_URL}/v1/videos/image2video"
            logger.info(f"Generating video from image: {input_image}")
        else:
            endpoint = f"{self.BASE_URL}/v1/videos/text2video"
            logger.info(f"Generating video with prompt: {prompt[:100]}...")

        logger.info(f"Model: {model}, Mode: {mode}, Duration: {duration}s, Aspect: {aspect_ratio}")

        # Build request payload
        payload = {
            "model_name": model,
            "mode": mode,
            "prompt": prompt,
            "duration": str(duration),
            "aspect_ratio": aspect_ratio,
            "cfg_scale": kwargs.get("cfg_scale", 0.5),
        }

        # Add negative prompt if provided
        if kwargs.get("negative_prompt"):
            payload["negative_prompt"] = kwargs["negative_prompt"]

        # Add camera control if provided
        if kwargs.get("camera_control"):
            payload["camera_control"] = kwargs["camera_control"]

        # Handle image input for image-to-video
        if input_image:
            if input_image.startswith("http"):
                payload["image"] = input_image
            else:
                # Upload local image (convert to base64)
                payload["image"] = self._upload_image(input_image)
                logger.info(f"Converted local image to base64")

            # End image for interpolation (optional, requires pro mode)
            if end_image:
                if end_image.startswith("http"):
                    payload["image_tail"] = end_image
                else:
                    payload["image_tail"] = self._upload_image(end_image)
                    logger.info(f"Converted end image to base64")
                # Auto-switch to pro mode when using end_image
                if mode != "pro":
                    logger.info("Switching to pro mode (required for end_image interpolation)")
                    payload["mode"] = "pro"

        # Handle video input for video extension
        if input_video:
            if input_video.startswith("http"):
                payload["video"] = input_video
            else:
                # For local video, we'd need to upload - for now require URL
                raise ValueError("Local video files not supported yet. Please provide a URL.")

        try:
            logger.info(f"Sending payload: {payload}")
            response = requests.post(
                endpoint,
                headers=self._get_headers(),
                json=payload,
                timeout=60
            )

            # Log response for debugging
            if response.status_code != 200:
                logger.error(f"API response ({response.status_code}): {response.text}")

            response.raise_for_status()
            result = response.json()

            if result.get("code") != 0:
                raise Exception(f"API error: {result.get('message', 'Unknown error')}")

            task_id = result.get("data", {}).get("task_id")
            if not task_id:
                raise Exception(f"No task_id in response: {result}")

            # Create job tracking
            job_id = f"kling_job_{task_id}"

            job_data = {
                "job_id": job_id,
                "task_id": task_id,
                "status": "PROCESSING",
                "model": model,
                "mode": mode,
                "prompt": prompt,
                "duration": duration,
                "aspect_ratio": aspect_ratio,
                "created_at": time.time(),
            }

            self.jobs[job_id] = task_id
            self.job_data[job_id] = job_data

            logger.info(f"Video generation started: {job_id} (task_id: {task_id})")

            return job_data

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response body: {e.response.text}")
                raise Exception(f"{str(e)} - Response: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error generating video: {str(e)}")
            raise

    def _query_task(self, task_id: str) -> Dict[str, Any]:
        """
        Query task status from Kling API

        Args:
            task_id: The task ID returned from generate_video

        Returns:
            Task status response
        """
        endpoint = f"{self.BASE_URL}/v1/videos/text2video/{task_id}"

        response = requests.get(
            endpoint,
            headers=self._get_headers(),
            timeout=30
        )
        response.raise_for_status()
        return response.json()

    def wait_for_completion(
        self,
        job_id: str,
        timeout: int = 600,
        poll_interval: int = 10
    ) -> Dict[str, Any]:
        """
        Wait for video generation to complete

        Args:
            job_id: Job identifier from generate_video
            timeout: Maximum wait time in seconds
            poll_interval: Time between status checks in seconds

        Returns:
            Dictionary with job status and output URL
        """
        logger.info(f"Waiting for job {job_id} to complete...")

        if job_id not in self.jobs:
            raise ValueError(f"Job {job_id} not found")

        task_id = self.jobs[job_id]
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                result = self._query_task(task_id)

                if result.get("code") != 0:
                    raise Exception(f"API error: {result.get('message')}")

                data = result.get("data", {})
                task_status = data.get("task_status")

                if task_status == "succeed":
                    # Get video URL from results
                    videos = data.get("task_result", {}).get("videos", [])
                    if videos:
                        video_url = videos[0].get("url")
                        video_duration = videos[0].get("duration")

                        self.job_data[job_id]["status"] = "COMPLETED"
                        self.job_data[job_id]["output_url"] = video_url
                        self.job_data[job_id]["video_duration"] = video_duration
                        self.job_data[job_id]["completed_at"] = time.time()

                        logger.info(f"Job {job_id} completed successfully")
                        logger.info(f"Video URL: {video_url}")

                        return {
                            "job_id": job_id,
                            "status": "COMPLETED",
                            "output_url": video_url,
                            "video_duration": video_duration,
                            "completed_at": time.time(),
                        }
                    else:
                        raise Exception("No videos in result")

                elif task_status == "failed":
                    error_msg = data.get("task_status_msg", "Unknown error")
                    self.job_data[job_id]["status"] = "FAILED"
                    self.job_data[job_id]["error"] = error_msg
                    raise Exception(f"Video generation failed: {error_msg}")

                else:
                    # Still processing
                    elapsed = int(time.time() - start_time)
                    logger.info(f"Job {job_id} status: {task_status} (elapsed: {elapsed}s)")
                    time.sleep(poll_interval)

            except requests.exceptions.RequestException as e:
                logger.warning(f"Request error while polling: {e}")
                time.sleep(poll_interval)

        raise TimeoutError(f"Job {job_id} did not complete within {timeout} seconds")

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

        # Download video from URL
        try:
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)

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
        """Get status of a video generation job"""
        if job_id not in self.job_data:
            raise ValueError(f"Job {job_id} not found")

        return self.job_data[job_id]

    def list_models(self) -> Dict[str, Any]:
        """List available models"""
        return self.MODELS
