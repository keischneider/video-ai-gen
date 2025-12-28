"""
Main workflow orchestrator for video generation pipeline
"""
import os
import logging
from typing import Optional, Union
from pathlib import Path

from src.clients.tts_client import TTSClient
from src.clients.lipsync_client import LipSyncClient
from src.utils.video_processor import VideoProcessor
from src.utils.scene_manager import SceneManager
from src.models.prompt import VideoPrompt, SceneConfig

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_video_client():
    """
    Factory function to get the appropriate video generation client
    based on VIDEO_PROVIDER environment variable.

    Supported providers:
        - "veo": Google Veo API (expensive, high quality)
        - "replicate": Replicate API with Wan models (cheap, good quality)
        - "sora": OpenAI Sora API (medium cost, excellent quality)

    Returns:
        VeoClient, ReplicateClient, or SoraClient based on configuration
    """
    provider = os.getenv("VIDEO_PROVIDER", "veo").lower()

    if provider == "replicate":
        from src.clients.replicate_client import ReplicateClient
        logger.info("Using Replicate API (cheap mode - ~$0.05/video)")
        return ReplicateClient()
    elif provider == "sora":
        from src.clients.sora_client import SoraClient
        logger.info("Using OpenAI Sora API (~$0.50-2.50/video)")
        return SoraClient()
    else:
        from src.clients.veo_client import VeoClient
        logger.info("Using Google Veo API (expensive - ~$1.75/video)")
        return VeoClient()


class VideoProductionWorkflow:
    """
    Orchestrates the complete video production workflow:
    1. Generate video with Veo
    2. Download and convert to ProRes
    3. Generate TTS audio
    4. Apply lip-sync
    5. Convert final video to ProRes
    """

    def __init__(
        self,
        projects_root: str = "./projects",
        project_name: str = "default",
        prores_profile: int = 2
    ):
        """
        Initialize workflow

        Args:
            projects_root: Root directory for all projects
            project_name: Name of the specific project (e.g., 'kremlin', 'sveta-running-kherson')
            prores_profile: ProRes profile (0=Proxy, 1=LT, 2=422, 3=422HQ)
        """
        self.projects_root = projects_root
        self.project_name = project_name

        # Initialize clients - use factory for video client
        self.video_client = get_video_client()
        self.tts_client = TTSClient()
        self.lipsync_client = LipSyncClient()
        self.video_processor = VideoProcessor(prores_profile=prores_profile)
        self.scene_manager = SceneManager(projects_root=projects_root, project_name=project_name)

        logger.info(f"Initialized VideoProductionWorkflow for project '{project_name}'")

    def process_scene(
        self,
        scene_config: SceneConfig,
        voice_id: Optional[str] = None,
        skip_lipsync: bool = False,
        input_video: Optional[str] = None,
        input_image: Optional[str] = None
    ) -> dict:
        """
        Process a complete scene through the pipeline

        Args:
            scene_config: Scene configuration with prompt
            voice_id: Optional voice ID for TTS
            skip_lipsync: Skip lip-sync step if True
            input_video: Optional path to input video for extension or GCS URI
            input_image: Optional path to input image for image-to-video (first frame)

        Returns:
            Dictionary with paths to generated files
        """
        scene_id = scene_config.scene_id
        prompt = scene_config.prompt

        logger.info(f"=== Processing {scene_id} ===")

        # Create scene folder
        scene_path = self.scene_manager.create_scene(scene_id)
        self.scene_manager.update_scene_status(scene_id, "generating_video")

        # Get provider and model info
        provider = os.getenv("VIDEO_PROVIDER", "veo")
        model = None
        if provider == "replicate":
            model = os.getenv("REPLICATE_MODEL", "wan-2.2-t2v-fast")
        elif provider == "sora":
            model = os.getenv("SORA_MODEL", "sora-2")
        elif provider == "veo":
            model = os.getenv("VEO_MODEL", "veo-2.0-generate-001")

        # Save generation info to metadata
        veo_prompt = prompt.to_veo_prompt()
        dialogue = prompt.get_dialogue()
        self.scene_manager.save_generation_info(
            scene_id=scene_id,
            prompt=veo_prompt,
            input_video=input_video,
            input_image=input_image,
            provider=provider,
            model=model,
            dialogue=dialogue if dialogue and dialogue.strip() else None
        )

        result = {
            "scene_id": scene_id,
            "scene_path": scene_path
        }

        try:
            # Step 1: Generate video
            if input_image:
                logger.info(f"Step 1: Generating video from image with {provider}")
                logger.info(f"Input image: {input_image}")
            elif input_video:
                logger.info(f"Step 1: Extending video with {provider}")
                logger.info(f"Input video: {input_video}")
            else:
                logger.info(f"Step 1: Generating video with {provider}")

            veo_prompt = prompt.to_veo_prompt()
            logger.info(f"Veo prompt: {veo_prompt}")

            job = self.video_client.generate_video(
                prompt=veo_prompt,
                input_video=input_video,
                input_image=input_image
            )
            job_status = self.video_client.wait_for_completion(job["job_id"])

            logger.info(f"Video generated successfully")

            # Step 2: Save video and convert to ProRes
            logger.info(f"Step 2: Saving video and converting to ProRes")
            self.scene_manager.update_scene_status(scene_id, "processing")

            raw_video_path = os.path.join(scene_path, f"{scene_id}_raw.mp4")
            self.video_client.save_video(job["job_id"], raw_video_path)

            prores_path = os.path.join(scene_path, f"{scene_id}_prores.mov")
            self.video_processor.convert_to_prores(raw_video_path, prores_path)

            self.scene_manager.save_file_reference(scene_id, "raw_video", raw_video_path)
            self.scene_manager.save_file_reference(scene_id, "prores_video", prores_path)

            result["raw_video"] = raw_video_path
            result["prores_video"] = prores_path

            # Step 3: Generate TTS audio (if dialogue exists)
            dialogue = prompt.get_dialogue()

            if dialogue and dialogue.strip():
                logger.info(f"Step 3: Generating TTS audio")
                self.scene_manager.update_scene_status(scene_id, "generating_audio")

                audio_path = os.path.join(scene_path, f"{scene_id}_dialogue.wav")
                self.tts_client.generate_speech(
                    text=dialogue,
                    output_path=audio_path,
                    voice_id=voice_id
                )

                self.scene_manager.save_file_reference(scene_id, "audio", audio_path)
                result["audio"] = audio_path

                # Step 4: Apply lip-sync
                if not skip_lipsync:
                    logger.info(f"Step 4: Applying lip-sync")
                    self.scene_manager.update_scene_status(scene_id, "lip_syncing")

                    synced_path = os.path.join(scene_path, f"{scene_id}_synced.mp4")
                    self.lipsync_client.create_and_wait(
                        video_path=raw_video_path,
                        audio_path=audio_path,
                        output_path=synced_path
                    )

                    # Step 5: Convert synced video to ProRes
                    logger.info(f"Step 5: Converting synced video to ProRes")
                    final_prores_path = os.path.join(
                        scene_path,
                        f"{scene_id}_final_prores.mov"
                    )
                    self.video_processor.convert_to_prores(
                        synced_path,
                        final_prores_path
                    )

                    self.scene_manager.save_file_reference(
                        scene_id,
                        "synced_video",
                        synced_path
                    )
                    self.scene_manager.save_file_reference(
                        scene_id,
                        "final_prores",
                        final_prores_path
                    )

                    result["synced_video"] = synced_path
                    result["final_prores"] = final_prores_path
                else:
                    logger.info("Skipping lip-sync step")
                    result["final_prores"] = prores_path
            else:
                logger.info("No dialogue provided, skipping audio and lip-sync")
                result["final_prores"] = prores_path

            # Mark as completed
            self.scene_manager.update_scene_status(scene_id, "completed")
            logger.info(f"=== {scene_id} completed successfully ===")

            return result

        except Exception as e:
            logger.error(f"Error processing {scene_id}: {str(e)}")
            self.scene_manager.update_scene_status(scene_id, "failed")
            raise

    def process_multiple_scenes(
        self,
        scene_configs: list[SceneConfig],
        voice_id: Optional[str] = None,
        skip_lipsync: bool = False
    ) -> list[dict]:
        """
        Process multiple scenes

        Args:
            scene_configs: List of scene configurations
            voice_id: Optional voice ID for TTS
            skip_lipsync: Skip lip-sync step if True

        Returns:
            List of results for each scene
        """
        results = []

        for config in scene_configs:
            try:
                result = self.process_scene(
                    config,
                    voice_id=voice_id,
                    skip_lipsync=skip_lipsync
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to process {config.scene_id}: {str(e)}")
                results.append({
                    "scene_id": config.scene_id,
                    "error": str(e)
                })

        return results

    def get_project_status(self) -> dict:
        """
        Get status of all scenes in the project

        Returns:
            Dictionary with project status
        """
        return self.scene_manager.get_project_structure()
