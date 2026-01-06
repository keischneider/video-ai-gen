#!/usr/bin/env python3.12
"""
CLI interface for VEO-FCP video generation pipeline
"""
import os
import sys
import json
import re
import click
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.workflow import VideoProductionWorkflow
from src.models.prompt import VideoPrompt, SceneConfig

# Load environment variables
load_dotenv()

console = Console()


def increment_scene_id(scene_id: str, increment: int = 1) -> str:
    """
    Increment the numeric portion of a scene ID.
    Examples:
        scene_01 + 1 -> scene_02
        scene_99 + 1 -> scene_100
        shot_5 + 3 -> shot_8
        my_scene_001 + 1 -> my_scene_002
    """
    # Find the last sequence of digits in the scene_id
    match = re.search(r'(\d+)(?!.*\d)', scene_id)
    if match:
        num_str = match.group(1)
        num = int(num_str) + increment
        # Preserve leading zeros (use original width as minimum)
        new_num_str = str(num).zfill(len(num_str))
        # Replace the matched number with the incremented one
        return scene_id[:match.start()] + new_num_str + scene_id[match.end():]
    else:
        # No number found, append the increment
        return f"{scene_id}_{increment}"


@click.group()
def cli():
    """VEO-FCP: Video Generation Pipeline for Final Cut Pro"""
    pass


@cli.command()
@click.option('--scene-id', required=True, help='Scene identifier (e.g., scene_01)')
@click.option('--prompt', required=True, help='Cinematic description')
@click.option('--character', help='Character consistency notes')
@click.option('--camera', help='Camera movement')
@click.option('--lighting', help='Lighting and style')
@click.option('--emotion', help='Emotion and facial performance')
@click.option('--dialogue', help='Dialogue text for TTS and lip-sync')
@click.option('--voice-id', help='ElevenLabs voice ID')
@click.option('--input-video', help='Path to input video for extension (1-30s) or GCS URI (gs://...)')
@click.option('--input-image', help='Path to input image for image-to-video (first frame)')
@click.option('--end-image', help='Path to end image for video interpolation (Kling pro mode)')
@click.option('--negative-prompt', help='Things to avoid in the video (Kling)')
@click.option('--duration', type=int, default=5, help='Video duration in seconds (Kling: 5/10, Veo: 4/6/8)')
@click.option('--seed', type=int, help='Random seed for reproducible generation')
@click.option('--skip-lipsync', is_flag=True, help='Skip lip-sync step')
@click.option('--analyze', is_flag=True, help='Analyze video with Claude after generation')
@click.option('--projects-root', default='./projects', help='Root directory for all projects')
@click.option('--project-name', default='default', help='Project name (e.g., kremlin, sveta-running-kherson)')
@click.option('--count', type=int, default=1, help='Number of times to run generation, incrementing scene ID each time')
def generate(scene_id, prompt, character, camera, lighting, emotion, dialogue,
             voice_id, input_video, input_image, end_image, negative_prompt, duration, seed, skip_lipsync, analyze, projects_root, project_name, count):
    """Generate a video scene with optional TTS and lip-sync"""

    console.print(f"\n[bold cyan]VEO-FCP Video Generation Pipeline[/bold cyan]")
    console.print(f"Project: [yellow]{project_name}[/yellow]")
    if count > 1:
        console.print(f"Generating [yellow]{count}[/yellow] scenes starting from [yellow]{scene_id}[/yellow]\n")
    else:
        console.print(f"Scene: [yellow]{scene_id}[/yellow]\n")

    # Initialize workflow once
    workflow = VideoProductionWorkflow(projects_root=projects_root, project_name=project_name)

    # Track results for summary when count > 1
    all_results = []
    failed_scenes = []

    for i in range(count):
        # Calculate current scene ID
        current_scene_id = increment_scene_id(scene_id, i) if i > 0 else scene_id

        if count > 1:
            console.print(f"\n[bold blue]{'─' * 50}[/bold blue]")
            console.print(f"[bold cyan]Processing scene {i + 1}/{count}:[/bold cyan] [yellow]{current_scene_id}[/yellow]")

        # Create video prompt
        video_prompt = VideoPrompt(
            cinematic_description=prompt,
            character_consistency=character,
            camera_movement=camera,
            lighting_style=lighting,
            emotion_performance=emotion,
            dialogue_text=dialogue
        )

        # Create scene config
        scene_config = SceneConfig(
            scene_id=current_scene_id,
            prompt=video_prompt
        )

        # Process scene
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Processing scene...", total=None)

                result = workflow.process_scene(
                    scene_config,
                    voice_id=voice_id,
                    skip_lipsync=skip_lipsync,
                    input_video=input_video,
                    input_image=input_image,
                    end_image=end_image,
                    negative_prompt=negative_prompt,
                    duration=duration,
                    seed=seed
                )

            all_results.append(result)

            # Display results
            console.print("\n[bold green]✓ Scene generated successfully![/bold green]\n")

            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("File Type", style="cyan")
            table.add_column("Path", style="yellow")

            for key, value in result.items():
                if key not in ['scene_id', 'scene_path'] and value:
                    table.add_row(key.replace('_', ' ').title(), value)

            console.print(table)
            console.print(f"\nFinal ProRes video: [green]{result.get('final_prores')}[/green]\n")

            # Run video analysis if requested
            if analyze:
                console.print("[bold cyan]Running video analysis with Claude...[/bold cyan]\n")
                try:
                    from src.clients.claude_client import ClaudeClient
                    from src.utils.scene_manager import SceneManager

                    claude_client = ClaudeClient()
                    scene_manager = SceneManager(projects_root=projects_root, project_name=project_name)

                    # Find the video to analyze (prefer raw, then prores)
                    video_to_analyze = result.get('raw_video') or result.get('final_prores')

                    if video_to_analyze and os.path.exists(video_to_analyze):
                        with Progress(
                            SpinnerColumn(),
                            TextColumn("[progress.description]{task.description}"),
                            console=console
                        ) as progress:
                            task = progress.add_task("Analyzing video with Claude...", total=None)

                            description = claude_client.analyze_video(
                                video_to_analyze,
                                include_generation_prompt=prompt
                            )
                            short_desc = claude_client.generate_short_description(video_to_analyze)

                        # Save to metadata
                        scene_manager.save_video_description(
                            scene_id=current_scene_id,
                            description=description,
                            short_description=short_desc
                        )

                        console.print("[bold green]✓ Video analysis complete![/bold green]\n")
                        console.print("[bold magenta]Short Description:[/bold magenta]")
                        console.print(f"{short_desc}\n")
                    else:
                        console.print("[yellow]Warning: Could not find video file for analysis[/yellow]\n")

                except Exception as e:
                    console.print(f"[yellow]Warning: Video analysis failed: {str(e)}[/yellow]\n")

        except Exception as e:
            failed_scenes.append((current_scene_id, str(e)))
            console.print(f"\n[bold red]✗ Error generating {current_scene_id}:[/bold red] {str(e)}\n")
            if count == 1:
                sys.exit(1)
            # Continue with next scene if count > 1

    # Print summary if multiple scenes were processed
    if count > 1:
        console.print(f"\n[bold blue]{'═' * 50}[/bold blue]")
        console.print(f"[bold cyan]Generation Summary[/bold cyan]")
        console.print(f"  Successful: [green]{len(all_results)}[/green]")
        console.print(f"  Failed: [red]{len(failed_scenes)}[/red]")

        if failed_scenes:
            console.print("\n[bold red]Failed scenes:[/bold red]")
            for scene, error in failed_scenes:
                console.print(f"  • {scene}: {error}")

        if failed_scenes:
            sys.exit(1)


@cli.command()
@click.option('--config-file', required=True, type=click.Path(exists=True),
              help='JSON config file with scene definitions')
@click.option('--voice-id', help='ElevenLabs voice ID')
@click.option('--skip-lipsync', is_flag=True, help='Skip lip-sync step')
@click.option('--projects-root', default='./projects', help='Root directory for all projects')
@click.option('--project-name', default='default', help='Project name (e.g., kremlin, sveta-running-kherson)')
def batch(config_file, voice_id, skip_lipsync, projects_root, project_name):
    """Process multiple scenes from a config file"""

    console.print(f"\n[bold cyan]VEO-FCP Batch Processing[/bold cyan]")
    console.print(f"Project: [yellow]{project_name}[/yellow]\n")

    # Load config file
    with open(config_file, 'r') as f:
        config_data = json.load(f)

    scenes = config_data.get('scenes', [])
    console.print(f"Processing {len(scenes)} scenes...\n")

    # Create scene configs
    scene_configs = []
    for scene_data in scenes:
        video_prompt = VideoPrompt(**scene_data['prompt'])
        scene_config = SceneConfig(
            scene_id=scene_data['scene_id'],
            prompt=video_prompt
        )
        scene_configs.append(scene_config)

    # Initialize workflow
    workflow = VideoProductionWorkflow(projects_root=projects_root, project_name=project_name)

    # Process scenes
    try:
        results = workflow.process_multiple_scenes(
            scene_configs,
            voice_id=voice_id,
            skip_lipsync=skip_lipsync
        )

        # Display results
        console.print("\n[bold green]Batch processing complete![/bold green]\n")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Scene ID", style="cyan")
        table.add_column("Status", style="yellow")
        table.add_column("Final ProRes", style="green")

        for result in results:
            scene_id = result.get('scene_id', 'Unknown')
            if 'error' in result:
                table.add_row(scene_id, "[red]Failed[/red]", result['error'])
            else:
                table.add_row(
                    scene_id,
                    "[green]Success[/green]",
                    result.get('final_prores', 'N/A')
                )

        console.print(table)
        console.print()

    except Exception as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {str(e)}\n")
        sys.exit(1)


@cli.command()
@click.option('--projects-root', default='./projects', help='Root directory for all projects')
@click.option('--project-name', default='default', help='Project name (e.g., kremlin, sveta-running-kherson)')
def status(projects_root, project_name):
    """Show project status"""

    workflow = VideoProductionWorkflow(projects_root=projects_root, project_name=project_name)
    project_status = workflow.get_project_status()

    console.print(f"\n[bold cyan]Project Status[/bold cyan]")
    console.print(f"Project: [yellow]{project_status['project_name']}[/yellow]")
    console.print(f"Path: [yellow]{project_status['project_dir']}[/yellow]\n")

    if not project_status['scenes']:
        console.print("[yellow]No scenes found[/yellow]\n")
        return

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Scene ID", style="cyan")
    table.add_column("Status", style="yellow")
    table.add_column("Files", style="green")

    for scene_id, scene_info in project_status['scenes'].items():
        status_color = {
            'completed': 'green',
            'failed': 'red',
            'generating_video': 'yellow',
            'downloading': 'yellow',
            'generating_audio': 'yellow',
            'lip_syncing': 'yellow',
        }.get(scene_info['status'], 'white')

        table.add_row(
            scene_id,
            f"[{status_color}]{scene_info['status']}[/{status_color}]",
            ", ".join(scene_info['files'])
        )

    console.print(table)
    console.print()


@cli.command()
@click.option('--text', required=True, help='Text to convert to speech')
@click.option('--output', required=True, help='Output audio file path (e.g., output.wav)')
@click.option('--voice-id', help='ElevenLabs voice ID (uses default from .env if not specified)')
def tts(text, output, voice_id):
    """Generate speech from text using ElevenLabs TTS"""

    console.print(f"\n[bold cyan]ElevenLabs TTS Generation[/bold cyan]\n")
    console.print(f"Text: [yellow]{text[:100]}{'...' if len(text) > 100 else ''}[/yellow]\n")

    try:
        from src.clients.tts_client import TTSClient

        # Initialize TTS client
        tts_client = TTSClient()

        # Generate speech
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Generating speech...", total=None)

            tts_client.generate_speech(
                text=text,
                output_path=output,
                voice_id=voice_id
            )

        console.print(f"\n[bold green]✓ Speech generated successfully![/bold green]")
        console.print(f"Output file: [green]{output}[/green]\n")

    except Exception as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {str(e)}\n")
        sys.exit(1)


@cli.command()
@click.option('--scene-id', required=True, help='Scene identifier to analyze')
@click.option('--projects-root', default='./projects', help='Root directory for all projects')
@click.option('--project-name', default='default', help='Project name')
@click.option('--video-path', help='Direct path to video file (overrides scene lookup)')
@click.option('--include-tags', is_flag=True, help='Also generate searchable tags')
def analyze(scene_id, projects_root, project_name, video_path, include_tags):
    """Analyze video with Claude and generate description"""

    console.print(f"\n[bold cyan]Video Analysis with Claude[/bold cyan]")
    console.print(f"Project: [yellow]{project_name}[/yellow]")
    console.print(f"Scene: [yellow]{scene_id}[/yellow]\n")

    try:
        from src.clients.claude_client import ClaudeClient
        from src.utils.scene_manager import SceneManager

        # Initialize clients
        claude_client = ClaudeClient()
        scene_manager = SceneManager(projects_root=projects_root, project_name=project_name)

        # Get video path
        if video_path:
            target_video = video_path
        else:
            # Try to find video in scene metadata
            target_video = scene_manager.get_file_path(scene_id, "raw_video")
            if not target_video or not os.path.exists(target_video):
                target_video = scene_manager.get_file_path(scene_id, "prores_video")

            # If metadata paths don't exist, look directly in scene directory
            if not target_video or not os.path.exists(target_video):
                scene_dir = Path(scene_manager.get_scene_path(scene_id))
                # Look for common video patterns
                for pattern in ["*_raw.mp4", "*.mp4", "*_prores.mov", "*.mov"]:
                    matches = list(scene_dir.glob(pattern))
                    if matches:
                        target_video = str(matches[0])
                        break

        if not target_video or not os.path.exists(target_video):
            console.print("[bold red]✗ No video found for this scene[/bold red]")
            sys.exit(1)

        console.print(f"Analyzing: [yellow]{target_video}[/yellow]\n")

        # Get generation prompt for context
        metadata = scene_manager.get_scene_metadata(scene_id)
        gen_prompt = metadata.get("generation", {}).get("prompt")

        # Analyze video
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Extracting frames and analyzing with Claude...", total=None)

            description = claude_client.analyze_video(
                target_video,
                include_generation_prompt=gen_prompt
            )

            short_desc = claude_client.generate_short_description(target_video)

            tags = []
            if include_tags:
                progress.update(task, description="Generating tags...")
                tags = claude_client.generate_tags(target_video)

        # Save to metadata
        scene_manager.save_video_description(
            scene_id=scene_id,
            description=description,
            short_description=short_desc,
            tags=tags
        )

        # Display results
        console.print("[bold green]✓ Video analysis complete![/bold green]\n")

        console.print("[bold magenta]Short Description:[/bold magenta]")
        console.print(f"{short_desc}\n")

        console.print("[bold magenta]Full Description:[/bold magenta]")
        console.print(f"{description}\n")

        if tags:
            console.print("[bold magenta]Tags:[/bold magenta]")
            console.print(", ".join(tags))
            console.print()

        console.print(f"[dim]Description saved to metadata.json[/dim]\n")

    except Exception as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {str(e)}\n")
        sys.exit(1)


@cli.command('download-youtube')
@click.option('--url', required=True, help='YouTube video URL')
@click.option('--scene-id', required=True, help='Scene identifier for the downloaded video')
@click.option('--projects-root', default='./projects', help='Root directory for all projects')
@click.option('--project-name', default='default', help='Project name')
@click.option('--quality', default='best', type=click.Choice(['best', '1080p', '720p', '480p', 'worst']),
              help='Video quality preset')
@click.option('--max-height', type=int, help='Maximum video height (e.g., 1080, 720)')
@click.option('--audio-only', is_flag=True, help='Download only audio (WAV format)')
@click.option('--to-prores', is_flag=True, help='Convert to ProRes after download')
@click.option('--analyze', is_flag=True, help='Analyze video with Claude after download')
def download_youtube(url, scene_id, projects_root, project_name, quality, max_height, audio_only, to_prores, analyze):
    """Download video from YouTube using yt-dlp"""

    console.print(f"\n[bold cyan]YouTube Video Download[/bold cyan]")
    console.print(f"Project: [yellow]{project_name}[/yellow]")
    console.print(f"Scene: [yellow]{scene_id}[/yellow]\n")

    try:
        from src.clients.youtube_client import YouTubeClient
        from src.utils.scene_manager import SceneManager
        from src.utils.video_processor import VideoProcessor

        # Initialize clients
        youtube_client = YouTubeClient()
        scene_manager = SceneManager(projects_root=projects_root, project_name=project_name)
        video_processor = VideoProcessor()

        # Get video info first
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Fetching video info...", total=None)
            video_info = youtube_client.get_video_info(url)

        console.print(f"Title: [yellow]{video_info.get('title', 'Unknown')}[/yellow]")
        console.print(f"Duration: [yellow]{video_info.get('duration', 0)}s[/yellow]")
        console.print(f"Resolution: [yellow]{video_info.get('width', '?')}x{video_info.get('height', '?')}[/yellow]\n")

        # Setup scene directory
        scene_dir = scene_manager.get_scene_path(scene_id)
        os.makedirs(scene_dir, exist_ok=True)

        # Download
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            if audio_only:
                task = progress.add_task("Downloading audio...", total=None)
                output_base = os.path.join(scene_dir, f"{scene_id}_audio")
                downloaded_path = youtube_client.download_audio(url, output_base)
            else:
                task = progress.add_task("Downloading video...", total=None)
                output_base = os.path.join(scene_dir, f"{scene_id}_raw")
                downloaded_path = youtube_client.download_video(
                    url, output_base, quality=quality, max_height=max_height
                )

        console.print(f"\n[bold green]✓ Downloaded:[/bold green] {downloaded_path}")

        # Convert to ProRes if requested
        prores_path = None
        if to_prores and not audio_only:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("Converting to ProRes...", total=None)
                prores_path = os.path.join(scene_dir, f"{scene_id}_prores.mov")
                video_processor.convert_to_prores(downloaded_path, prores_path)

            console.print(f"[bold green]✓ ProRes:[/bold green] {prores_path}")

        # Update scene metadata
        scene_manager.update_scene_metadata(scene_id, {
            'status': 'completed',
            'source': {
                'type': 'youtube',
                'url': url,
                'title': video_info.get('title'),
                'duration': video_info.get('duration'),
                'video_id': video_info.get('id'),
            },
            'files': {
                'raw_video': {'path': downloaded_path} if not audio_only else None,
                'audio': {'path': downloaded_path} if audio_only else None,
                'prores_video': {'path': prores_path} if prores_path else None,
            }
        })

        # Analyze if requested
        if analyze and not audio_only:
            console.print("\n[bold cyan]Running video analysis with Claude...[/bold cyan]")
            try:
                from src.clients.claude_client import ClaudeClient

                claude_client = ClaudeClient()
                video_to_analyze = prores_path or downloaded_path

                with Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    console=console
                ) as progress:
                    task = progress.add_task("Analyzing video...", total=None)
                    description = claude_client.analyze_video(video_to_analyze)
                    short_desc = claude_client.generate_short_description(video_to_analyze)

                scene_manager.save_video_description(
                    scene_id=scene_id,
                    description=description,
                    short_description=short_desc
                )

                console.print(f"\n[bold magenta]Description:[/bold magenta] {short_desc}")

            except Exception as e:
                console.print(f"[yellow]Warning: Video analysis failed: {str(e)}[/yellow]")

        console.print(f"\n[bold green]✓ YouTube download complete![/bold green]\n")

    except Exception as e:
        console.print(f"\n[bold red]✗ Error:[/bold red] {str(e)}\n")
        sys.exit(1)


@cli.command()
def setup():
    """Setup wizard for configuration"""

    console.print("\n[bold cyan]VEO-FCP Setup Wizard[/bold cyan]\n")

    # Check if .env exists
    env_path = Path('.env')
    if env_path.exists():
        console.print("[yellow].env file already exists[/yellow]")
        if not click.confirm("Overwrite?"):
            return

    console.print("Please provide your API credentials:\n")

    # Collect credentials
    google_project = click.prompt("Google Cloud Project ID")
    google_creds = click.prompt("Path to Google service account JSON")
    elevenlabs_key = click.prompt("ElevenLabs API Key")
    did_key = click.prompt("D-ID API Key")

    # Write .env file
    env_content = f"""# Google Cloud Configuration for Veo API
GOOGLE_CLOUD_PROJECT={google_project}
GOOGLE_APPLICATION_CREDENTIALS={google_creds}
VEO_LOCATION=us-central1

# ElevenLabs TTS API
ELEVENLABS_API_KEY={elevenlabs_key}
ELEVENLABS_VOICE_ID=21m00Tcm4TlvDq8ikWAM

# D-ID Lip Sync API
DID_API_KEY={did_key}

# Project Configuration
PROJECTS_ROOT=./projects
PROJECT_NAME=default

# FFmpeg Configuration
FFMPEG_PRORES_PROFILE=2
"""

    with open('.env', 'w') as f:
        f.write(env_content)

    console.print("\n[bold green]✓ Configuration saved to .env[/bold green]")
    console.print("\nYou can now start using VEO-FCP!\n")


if __name__ == '__main__':
    cli()
