"""
Replicate API Client for video generation - cheap alternative to Veo
Supports Wan 2.2/2.5 models for text-to-video and image-to-video
"""
import os
import time
import logging
import requests
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class ReplicateClient:
    """Client for Replicate video generation API (Wan models)"""

    # Available models and their costs (approximate)
    MODELS = {
        "wan-2.2-t2v-fast": {
            "id": "wan-video/wan-2.2-t2v-fast",
            "type": "text-to-video",
            "cost_480p": 0.05,  # $0.05 per video
            "cost_720p": 0.10,
        },
        "wan-2.5-t2v-fast": {
            "id": "wan-video/wan-2.5-t2v-fast",
            "type": "text-to-video",
            "cost_480p": 0.08,
            "cost_720p": 0.15,
        },
        "wan-2.2-i2v-fast": {
            "id": "wan-video/wan-2.2-i2v-fast",
            "type": "image-to-video",
            "cost_480p": 0.05,
            "cost_720p": 0.10,
        },
        "wan-2.5-i2v-fast": {
            "id": "wan-video/wan-2.5-i2v-fast",
            "type": "image-to-video",
            "requires_image": True,
            "cost_720p": 0.08,
            "cost_1080p": 0.15,
            "durations": [5, 10],
            "default_duration": 5,
        },
        "kling-v2.1": {
            "id": "kwaivgi/kling-v2.1",
            "type": "image-to-video",
            "requires_image": True,
            "cost_480p": 0.25,  # standard: $0.05/s * 5s
            "cost_720p": 0.25,  # standard mode is 720p
            "cost_1080p": 0.45,  # pro: $0.09/s * 5s
        },
        "kling-v1.6-standard": {
            "id": "kwaivgi/kling-v1.6-standard",
            "type": "image-to-video",
            "requires_image": True,
            "cost_480p": 0.20,
            "cost_720p": 0.20,
        },
        "veo-3.1": {
            "id": "google/veo-3.1",
            "type": "text-to-video",  # Also supports image-to-video with 'image' param
            "requires_image": False,
            "cost_720p": 0.75,
            "cost_1080p": 1.00,
            "durations": [4, 6, 8],  # Supported durations
            "default_duration": 8,
        },
    }

    def __init__(self, api_token: Optional[str] = None):
        """
        Initialize Replicate API client

        Args:
            api_token: Replicate API token (or set REPLICATE_API_TOKEN env var)
        """
        self.api_token = api_token or os.getenv("REPLICATE_API_TOKEN")
        if not self.api_token:
            raise ValueError("REPLICATE_API_TOKEN is required")

        # Import replicate
        try:
            import replicate
            self.replicate = replicate
        except ImportError:
            raise ImportError("Please install replicate: pip install replicate")

        # Set the API token
        os.environ["REPLICATE_API_TOKEN"] = self.api_token

        # Get model preference from env
        self.default_model = os.getenv("REPLICATE_MODEL", "wan-2.2-t2v-fast")
        self.default_resolution = os.getenv("REPLICATE_RESOLUTION", "480p")

        # Store jobs for tracking
        self.jobs = {}
        self.job_data = {}

        logger.info(f"Initialized Replicate client with model: {self.default_model}")

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
        Generate video using Replicate API (Wan models)

        Args:
            prompt: Text prompt for video generation
            duration: Video duration in seconds (affects num_frames)
            aspect_ratio: Video aspect ratio (16:9 or 9:16)
            input_video: Optional path to input video for vid2vid (not fully supported yet)
            input_image: Optional path to input image for image-to-video
            **kwargs: Additional parameters (resolution, model, etc.)

        Returns:
            Dictionary with job information
        """
        # Determine model type based on inputs
        model_name = kwargs.get("model", self.default_model)
        resolution = kwargs.get("resolution", self.default_resolution)

        # If input_image provided, use i2v model
        if input_image:
            if "i2v" not in model_name:
                model_name = model_name.replace("t2v", "i2v")
                logger.info(f"Switched to image-to-video model: {model_name}")

        # If input_video provided, extract last frame and use i2v for continuation
        if input_video and not input_image:
            logger.info("Extracting last frame from input video for i2v continuation")
            input_image = self._extract_last_frame(input_video)
            if "i2v" not in model_name:
                model_name = model_name.replace("t2v", "i2v")

        model_info = self.MODELS.get(model_name)
        if not model_info:
            # Try to find a matching model
            for name, info in self.MODELS.items():
                if name in model_name or model_name in name:
                    model_info = info
                    model_name = name
                    break
            if not model_info:
                raise ValueError(f"Unknown model: {model_name}. Available: {list(self.MODELS.keys())}")

        # Validate image requirement for models that need it
        if model_info.get("requires_image") and not input_image:
            raise ValueError(f"Model {model_name} requires an input image (--input-image)")

        model_id = model_info["id"]

        # Calculate num_frames based on duration (16 fps default)
        # Wan models support 81-121 frames
        fps = kwargs.get("fps", 16)
        num_frames = min(max(duration * fps, 81), 121)

        logger.info(f"Generating video with {model_name}")
        logger.info(f"Prompt: {prompt[:100]}...")
        logger.info(f"Resolution: {resolution}, Frames: {num_frames}, Aspect: {aspect_ratio}")

        try:
            # For i2v models, enhance prompt with motion focus
            effective_prompt = prompt
            if input_image and model_info["type"] == "image-to-video":
                # I2V prompts should focus on motion and camera movement
                # The image already establishes the scene
                if not any(word in prompt.lower() for word in ['camera', 'pan', 'zoom', 'dolly', 'motion', 'moving', 'slowly', 'quickly']):
                    effective_prompt = f"{prompt}, cinematic motion, smooth camera movement"
                    logger.info(f"Enhanced i2v prompt: {effective_prompt}")

            # Handle Kling models separately (different API structure)
            if model_name in ["kling-v2.1", "kling-v1.6-standard"]:
                input_params = self._prepare_kling_params(
                    prompt=effective_prompt,
                    input_image=input_image,
                    duration=duration,
                    resolution=resolution,
                    negative_prompt=kwargs.get("negative_prompt", ""),
                    end_image=kwargs.get("end_image"),
                    seed=kwargs.get("seed"),
                )
            elif model_name == "wan-2.5-i2v-fast":
                input_params = self._prepare_wan25_i2v_params(
                    prompt=effective_prompt,
                    input_image=input_image,
                    duration=duration,
                    resolution=resolution,
                    negative_prompt=kwargs.get("negative_prompt", ""),
                    end_image=kwargs.get("end_image"),
                    seed=kwargs.get("seed"),
                )
            elif model_name == "veo-3.1":
                input_params = self._prepare_veo_params(
                    prompt=effective_prompt,
                    input_image=input_image,
                    duration=duration,
                    aspect_ratio=aspect_ratio,
                    resolution=resolution,
                    negative_prompt=kwargs.get("negative_prompt", ""),
                    end_image=kwargs.get("end_image"),
                    generate_audio=kwargs.get("generate_audio", True),
                    reference_images=kwargs.get("reference_images"),
                    seed=kwargs.get("seed"),
                )
            else:
                # Prepare input parameters for Wan models
                input_params = {
                    "prompt": effective_prompt,
                    "num_frames": num_frames,
                    "aspect_ratio": aspect_ratio,
                    "resolution": resolution,
                    "frames_per_second": fps,
                    "go_fast": True,
                    "sample_shift": kwargs.get("sample_shift", 8),  # Lower value = more prompt adherence
                    "interpolate_output": True,
                }

                # Add image input for i2v models
                if input_image and model_info["type"] == "image-to-video":
                    # Read image file and pass to replicate
                    if input_image.startswith("http"):
                        input_params["image"] = input_image
                    else:
                        input_params["image"] = open(input_image, "rb")

                # Add last_image for i2v models (end frame for interpolation)
                end_image = kwargs.get("end_image")
                if end_image and model_info["type"] == "image-to-video":
                    if end_image.startswith("http"):
                        input_params["last_image"] = end_image
                    else:
                        input_params["last_image"] = open(end_image, "rb")

            # Add seed if provided
            if kwargs.get("seed"):
                input_params["seed"] = kwargs["seed"]

            # Run the model (this blocks until complete)
            logger.info(f"Sending request to Replicate API...")
            start_time = time.time()

            output = self.replicate.run(model_id, input=input_params)

            elapsed = time.time() - start_time
            logger.info(f"Video generated in {elapsed:.1f}s")

            # Create job ID
            job_id = f"replicate_job_{int(time.time())}"

            # Store result
            job_data = {
                "job_id": job_id,
                "status": "COMPLETED",
                "model": model_name,
                "prompt": prompt,
                "duration": duration,
                "aspect_ratio": aspect_ratio,
                "resolution": resolution,
                "created_at": start_time,
                "completed_at": time.time(),
                "output_url": str(output) if isinstance(output, str) else output,
                "elapsed_seconds": elapsed,
            }

            self.jobs[job_id] = output
            self.job_data[job_id] = job_data

            logger.info(f"Video generation completed: {job_id}")
            if isinstance(output, str):
                logger.info(f"Output URL: {output}")

            return job_data

        except Exception as e:
            logger.error(f"Error generating video: {str(e)}")
            raise

    def _extract_first_frame(self, video_path: str) -> str:
        """Extract first frame from video for i2v generation"""
        import tempfile
        try:
            import ffmpeg
        except ImportError:
            raise ImportError("ffmpeg-python required for frame extraction")

        # Create temp file for frame
        temp_dir = tempfile.gettempdir()
        frame_path = os.path.join(temp_dir, f"frame_{int(time.time())}.jpg")

        try:
            # Extract first frame
            stream = ffmpeg.input(video_path)
            stream = ffmpeg.output(stream, frame_path, vframes=1, format='image2')
            ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)

            logger.info(f"Extracted first frame to: {frame_path}")
            return frame_path

        except Exception as e:
            logger.error(f"Error extracting frame: {e}")
            raise

    def _extract_last_frame(self, video_path: str) -> str:
        """Extract last frame from video for i2v continuation"""
        import tempfile
        try:
            import ffmpeg
        except ImportError:
            raise ImportError("ffmpeg-python required for frame extraction")

        # Create temp file for frame
        temp_dir = tempfile.gettempdir()
        frame_path = os.path.join(temp_dir, f"last_frame_{int(time.time())}.jpg")

        try:
            # Get video duration first
            probe = ffmpeg.probe(video_path)
            duration = float(probe['format']['duration'])

            # Seek to near the end and extract last frame
            # Use sseof to seek from end (more reliable for last frame)
            stream = ffmpeg.input(video_path, sseof=-0.1)  # 0.1 seconds from end
            stream = ffmpeg.output(stream, frame_path, vframes=1, format='image2', update=1)
            ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)

            logger.info(f"Extracted last frame to: {frame_path} (video duration: {duration:.1f}s)")
            return frame_path

        except Exception as e:
            logger.error(f"Error extracting last frame: {e}")
            # Fallback to first frame if last frame extraction fails
            logger.warning("Falling back to first frame extraction")
            return self._extract_first_frame(video_path)

    def _prepare_kling_params(
        self,
        prompt: str,
        input_image: Optional[str],
        duration: int = 5,
        resolution: str = "720p",
        negative_prompt: str = "",
        end_image: Optional[str] = None,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Prepare input parameters for Kling v2.1 model

        Args:
            prompt: Text prompt for video generation
            input_image: Path or URL to start image (required for Kling)
            duration: Video duration (5 or 10 seconds)
            resolution: "720p" for standard mode, "1080p" for pro mode
            negative_prompt: Things to avoid in the video
            end_image: Optional end frame (requires pro mode)
            seed: Random seed for reproducible generation

        Returns:
            Dictionary of input parameters for Kling API
        """
        if not input_image:
            raise ValueError("Kling v2.1 requires an input image (--input-image)")

        # Determine mode based on resolution
        if resolution == "1080p":
            mode = "pro"
        else:
            mode = "standard"

        # Kling only supports 5 or 10 second durations
        kling_duration = 10 if duration >= 8 else 5

        input_params = {
            "prompt": prompt,
            "duration": kling_duration,
            "mode": mode,
        }

        # Add start image
        if input_image.startswith("http"):
            input_params["start_image"] = input_image
        else:
            input_params["start_image"] = open(input_image, "rb")

        # Add optional parameters
        if negative_prompt:
            input_params["negative_prompt"] = negative_prompt

        if end_image:
            if end_image.startswith("http"):
                input_params["end_image"] = end_image
            else:
                input_params["end_image"] = open(end_image, "rb")

        if seed is not None:
            input_params["seed"] = seed

        logger.info(f"Kling params: mode={mode}, duration={kling_duration}s, seed={seed}")
        return input_params

    def _prepare_wan25_i2v_params(
        self,
        prompt: str,
        input_image: Optional[str],
        duration: int = 5,
        resolution: str = "720p",
        negative_prompt: str = "",
        end_image: Optional[str] = None,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Prepare input parameters for Wan 2.5 I2V Fast model

        Args:
            prompt: Text prompt for video generation
            input_image: Path or URL to input image (required)
            duration: Video duration (5 or 10 seconds)
            resolution: "720p" or "1080p"
            negative_prompt: Things to avoid in the video
            end_image: Optional end frame for interpolation (last_image)
            seed: Random seed for reproducible generation

        Returns:
            Dictionary of input parameters for Wan 2.5 I2V API
        """
        if not input_image:
            raise ValueError("Wan 2.5 I2V requires an input image (--input-image)")

        # Wan 2.5 I2V only supports 5 or 10 second durations
        wan_duration = 10 if duration >= 8 else 5

        # Validate resolution
        if resolution not in ["720p", "1080p"]:
            resolution = "720p"

        input_params = {
            "prompt": prompt,
            "duration": wan_duration,
            "resolution": resolution,
            "enable_prompt_expansion": True,
        }

        # Add image
        if input_image.startswith("http"):
            input_params["image"] = input_image
        else:
            input_params["image"] = open(input_image, "rb")

        # Add end image (last_image) for interpolation
        if end_image:
            if end_image.startswith("http"):
                input_params["last_image"] = end_image
            else:
                input_params["last_image"] = open(end_image, "rb")

        # Add negative prompt if provided
        if negative_prompt:
            input_params["negative_prompt"] = negative_prompt

        # Add seed if provided
        if seed is not None:
            input_params["seed"] = seed

        logger.info(f"Wan 2.5 I2V params: duration={wan_duration}s, resolution={resolution}, end_image={end_image is not None}, seed={seed}")
        return input_params

    def _prepare_veo_params(
        self,
        prompt: str,
        input_image: Optional[str] = None,
        duration: int = 8,
        aspect_ratio: str = "16:9",
        resolution: str = "1080p",
        negative_prompt: str = "",
        end_image: Optional[str] = None,
        generate_audio: bool = True,
        reference_images: Optional[list] = None,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Prepare input parameters for Google Veo 3.1 model

        Args:
            prompt: Text prompt for video generation
            input_image: Optional start image (ideal: 1280x720 or 720x1280)
            duration: Video duration (4, 6, or 8 seconds)
            aspect_ratio: "16:9" or "9:16"
            resolution: "720p" or "1080p"
            negative_prompt: Things to avoid in the video
            end_image: Optional end frame for interpolation
            generate_audio: Generate audio with video (default True)
            reference_images: 1-3 reference images for subject consistency (R2V)
            seed: Random seed for reproducible generation

        Returns:
            Dictionary of input parameters for Veo 3.1 API
        """
        # Veo 3.1 only supports 4, 6, or 8 second durations
        valid_durations = [4, 6, 8]
        veo_duration = min(valid_durations, key=lambda x: abs(x - duration))

        # Validate aspect ratio
        if aspect_ratio not in ["16:9", "9:16"]:
            logger.warning(f"Invalid aspect ratio {aspect_ratio}, defaulting to 16:9")
            aspect_ratio = "16:9"

        # Validate resolution
        if resolution not in ["720p", "1080p"]:
            resolution = "1080p"

        input_params = {
            "prompt": prompt,
            "duration": veo_duration,
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "generate_audio": generate_audio,
        }

        # Add start image if provided
        if input_image:
            if input_image.startswith("http"):
                input_params["image"] = input_image
            else:
                input_params["image"] = open(input_image, "rb")

        # Add end image for interpolation (last_frame)
        if end_image:
            if end_image.startswith("http"):
                input_params["last_frame"] = end_image
            else:
                input_params["last_frame"] = open(end_image, "rb")

        # Add negative prompt if provided
        if negative_prompt:
            input_params["negative_prompt"] = negative_prompt

        # Add reference images for subject consistency (R2V)
        # Note: Only works with 16:9 aspect ratio and 8-second duration
        if reference_images:
            if aspect_ratio != "16:9" or veo_duration != 8:
                logger.warning("Reference images only work with 16:9 aspect ratio and 8s duration")
            else:
                # Handle up to 3 reference images
                ref_images = []
                for ref_img in reference_images[:3]:
                    if ref_img.startswith("http"):
                        ref_images.append(ref_img)
                    else:
                        ref_images.append(open(ref_img, "rb"))
                input_params["reference_images"] = ref_images

        if seed is not None:
            input_params["seed"] = seed

        logger.info(f"Veo 3.1 params: duration={veo_duration}s, resolution={resolution}, aspect={aspect_ratio}, audio={generate_audio}, seed={seed}")
        return input_params

    def wait_for_completion(
        self,
        job_id: str,
        timeout: int = 600,
        poll_interval: int = 5
    ) -> Dict[str, Any]:
        """
        Wait for video generation to complete
        Note: replicate.run() already blocks, so this just returns the stored result

        Args:
            job_id: Job identifier
            timeout: Maximum wait time in seconds (not used - replicate.run blocks)
            poll_interval: Polling interval (not used)

        Returns:
            Dictionary with job status and output
        """
        if job_id not in self.job_data:
            raise ValueError(f"Job {job_id} not found")

        job_data = self.job_data[job_id]

        return {
            "job_id": job_id,
            "status": job_data["status"],
            "output_url": job_data.get("output_url"),
            "completed_at": job_data.get("completed_at"),
        }

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
            raise Exception("No output URL available for this job")

        # Download video from URL
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
        """Get status of a video generation job"""
        if job_id not in self.job_data:
            raise ValueError(f"Job {job_id} not found")

        return self.job_data[job_id]

    def list_models(self) -> Dict[str, Any]:
        """List available models and their costs"""
        return self.MODELS

    def estimate_cost(
        self,
        resolution: str = "480p",
        model: Optional[str] = None
    ) -> float:
        """Estimate cost for a single video generation"""
        model_name = model or self.default_model
        model_info = self.MODELS.get(model_name, {})

        if resolution == "720p":
            return model_info.get("cost_720p", 0.10)
        return model_info.get("cost_480p", 0.05)
