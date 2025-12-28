#!/usr/bin/env python3
"""
Example usage of VEO-FCP programmatically
"""
from dotenv import load_dotenv
from src.workflow import VideoProductionWorkflow
from src.models.prompt import VideoPrompt, SceneConfig

# Load environment variables
load_dotenv()


def example_single_scene():
    """Example: Generate a single scene"""
    print("=== Example 1: Single Scene Generation ===\n")

    # Create a video prompt with all details
    prompt = VideoPrompt(
        cinematic_description=(
            "A detective sits in a dimly lit office, rain streaming down "
            "the window behind him. He's reviewing case files under a "
            "single desk lamp."
        ),
        character_consistency="Male detective, 40s, grey suit, tired expression, stubble",
        camera_movement="Slow dolly in from wide shot to medium close-up",
        lighting_style="Film noir, high contrast, venetian blind shadows, single desk lamp",
        emotion_performance="Tired but determined, contemplative",
        dialogue_text="Every case has a missing piece. I just need to find it."
    )

    # Create scene configuration
    config = SceneConfig(
        scene_id="detective_office",
        prompt=prompt
    )

    # Initialize workflow
    workflow = VideoProductionWorkflow(projects_root="./projects", project_name="examples")

    # Process the scene
    try:
        result = workflow.process_scene(config)

        print("\nSuccess! Generated files:")
        print(f"  Raw video: {result['raw_video']}")
        print(f"  ProRes video: {result['prores_video']}")
        print(f"  Audio: {result.get('audio', 'N/A')}")
        print(f"  Final ProRes: {result['final_prores']}")
        print(f"\nImport {result['final_prores']} into Final Cut Pro!")

    except Exception as e:
        print(f"Error: {e}")


def example_multiple_scenes():
    """Example: Generate multiple scenes as a sequence"""
    print("\n=== Example 2: Multiple Scene Generation ===\n")

    # Define three scenes for a short story
    scenes = [
        SceneConfig(
            scene_id="scene_01_arrival",
            prompt=VideoPrompt(
                cinematic_description="A sleek spacecraft descends through clouds toward an alien planet",
                camera_movement="Wide establishing shot, following spacecraft descent",
                lighting_style="Dramatic atmospheric lighting, backlit by dual suns",
                emotion_performance="Awe-inspiring, majestic",
                dialogue_text="Command, we're beginning our descent to the surface."
            )
        ),
        SceneConfig(
            scene_id="scene_02_landing",
            prompt=VideoPrompt(
                cinematic_description="The spacecraft touches down on rocky alien terrain, dust billowing",
                camera_movement="Ground-level shot, low angle looking up at ship",
                lighting_style="Dusty atmosphere, orange-tinted sunlight, high contrast",
                emotion_performance="Tense, anticipation",
                dialogue_text="Landing sequence complete. All systems nominal."
            )
        ),
        SceneConfig(
            scene_id="scene_03_explorer",
            prompt=VideoPrompt(
                cinematic_description="Astronaut steps out of ship, looking at alien landscape horizon",
                character_consistency="Astronaut in white suit, reflective helmet visor",
                camera_movement="Medium shot from behind, looking over shoulder at vista",
                lighting_style="Warm alien sunset, lens flare, epic scale",
                emotion_performance="Wonder, determination, historic moment",
                dialogue_text="One small step for humanity, one giant leap for our species."
            )
        )
    ]

    # Initialize workflow
    workflow = VideoProductionWorkflow(projects_root="./projects", project_name="examples")

    # Process all scenes
    results = workflow.process_multiple_scenes(scenes)

    print("\nBatch processing complete!")
    for i, result in enumerate(results, 1):
        if 'error' in result:
            print(f"{i}. {result['scene_id']}: FAILED - {result['error']}")
        else:
            print(f"{i}. {result['scene_id']}: SUCCESS")
            print(f"   Final: {result['final_prores']}")


def example_no_dialogue():
    """Example: Generate scene without dialogue (skip TTS and lip-sync)"""
    print("\n=== Example 3: Scene Without Dialogue ===\n")

    # Create a scene with no dialogue (establishing shot)
    prompt = VideoPrompt(
        cinematic_description=(
            "Aerial drone shot soaring over a cyberpunk cityscape at night, "
            "neon signs and holographic billboards illuminating the streets below"
        ),
        camera_movement="Dynamic aerial drone flight, weaving between skyscrapers",
        lighting_style="Neon purple and blue, holographic glow, atmospheric fog",
        dialogue_text=None  # No dialogue
    )

    config = SceneConfig(
        scene_id="city_establishing",
        prompt=prompt
    )

    workflow = VideoProductionWorkflow(projects_root="./projects", project_name="examples")

    try:
        # Process without lip-sync (automatically skipped when no dialogue)
        result = workflow.process_scene(config)

        print("\nSuccess! Generated files:")
        print(f"  Final ProRes: {result['final_prores']}")
        print(f"\nNote: No audio/lip-sync was generated (no dialogue provided)")

    except Exception as e:
        print(f"Error: {e}")


def example_custom_voice():
    """Example: Use custom ElevenLabs voice"""
    print("\n=== Example 4: Custom Voice Selection ===\n")

    from src.clients.tts_client import TTSClient

    # List available voices
    tts_client = TTSClient()
    voices = tts_client.list_voices()

    print("Available voices:")
    for i, voice in enumerate(voices[:5], 1):
        print(f"  {i}. {voice.name} ({voice.voice_id})")

    # Use a specific voice
    prompt = VideoPrompt(
        cinematic_description="A news anchor delivers breaking news",
        character_consistency="Professional news anchor, formal attire",
        camera_movement="Static medium shot, centered framing",
        lighting_style="Studio lighting, clean and bright",
        emotion_performance="Professional, authoritative",
        dialogue_text="Breaking news: Scientists have made a groundbreaking discovery."
    )

    config = SceneConfig(scene_id="news_anchor", prompt=prompt)
    workflow = VideoProductionWorkflow(projects_root="./projects", project_name="examples")

    try:
        # Use specific voice ID (e.g., for male news anchor voice)
        result = workflow.process_scene(
            config,
            voice_id="pNInz6obpgDQGcFmaJgB"  # Adam voice
        )

        print(f"\nGenerated with custom voice: {result['final_prores']}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    # Run examples
    # Uncomment the example you want to run:

    example_single_scene()
    # example_multiple_scenes()
    # example_no_dialogue()
    # example_custom_voice()
