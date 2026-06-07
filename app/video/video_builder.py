import os
import subprocess
import random
import wave
from pathlib import Path
from app.core.config import config
from app.core.logger import setup_logging
from app.utils.helpers import VIDEO_DIR, IMAGES_DIR, get_audio_duration

log = setup_logging("video_builder")


def get_cinematic_motion(index, duration, width=1920, height=1080, fps=30):
    """
    Upgraded motion system with robust normalization.
    Every image is first converted to 1920x1080, then motion is applied.
    """
    direction = random.choice(["zoom_in", "zoom_out", "pan_left", "pan_right"])
    frames = int(duration * fps)
    
    # 1. BASE: Convert any aspect ratio to 1920x1080 (Fill frame)
    base = (
        f"[{index}:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},setsar=1"
    )
    
    if direction == "zoom_in":
        # First scale up slightly so zoompan has room without quality loss
        # Then zoom from 1.0 to 1.1
        return (
            f"{base},scale={width*2}:{height*2},"
            f"zoompan=z='min(zoom+0.0005,1.1)':x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':"
            f"d={frames}:s={width}x{height}[v{index}]"
        )
    elif direction == "zoom_out":
        # Zoom from 1.1 down to 1.0
        return (
            f"{base},scale={width*2}:{height*2},"
            f"zoompan=z='max(1.1-0.0005*on,1.0)':x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':"
            f"d={frames}:s={width}x{height}[v{index}]"
        )
    elif direction == "pan_left":
        # Scale to 110% of width, then crop-pan across it
        pan_w = int(width * 1.1)
        pan_h = int(height * 1.1)
        return (
            f"{base},scale={pan_w}:{pan_h},"
            f"crop={width}:{height}:'(iw-ow)*(t/{duration})':(ih-oh)/2[v{index}]"
        )
    elif direction == "pan_right":
        # Scale to 110% of width, then crop-pan across it
        pan_w = int(width * 1.1)
        pan_h = int(height * 1.1)
        return (
            f"{base},scale={pan_w}:{pan_h},"
            f"crop={width}:{height}:'(iw-ow)*(1-t/{duration})':(ih-oh)/2[v{index}]"
        )

    # Fallback to zoom in
    return (
        f"{base},scale={width*2}:{height*2},"
        f"zoompan=z='min(zoom+0.0005,1.1)':x='iw/2-(iw/zoom)/2':y='ih/2-(ih/zoom)/2':"
        f"d={frames}:s={width}x{height}[v{index}]"
    )


def build_video(image_paths, audio_file, sub_file=None):
    if not image_paths:
        raise RuntimeError("No images provided")
    if not os.path.exists(audio_file):
        raise RuntimeError(f"Audio file missing: {audio_file}")

    sub_path = sub_file or os.fspath(VIDEO_DIR / "subtitles.srt")
    if not os.path.exists(sub_path):
        raise RuntimeError(f"Subtitle file missing: {sub_path}")

    total_duration = get_audio_duration(audio_file)
    n_images = len(image_paths)
    fade_dur = 0.5 # User requested 0.4-0.6s
    
    # NEW DURATION MATH
    # per_image = (total_duration + (N-1)*fade_duration) / N
    per_image = (total_duration + (n_images - 1) * fade_dur) / n_images
    
    log.info(f"Building video: {n_images} scenes, {total_duration:.2f}s total, {per_image:.2f}s/image")

    image_inputs = []
    for img in image_paths:
        image_inputs.extend(["-loop", "1", "-t", str(per_image), "-i", img])

    filter_parts = []

    for i in range(n_images):
        effect = get_cinematic_motion(i, per_image, config.video_width, config.video_height, config.video_fps)
        filter_parts.append(effect)

    last = "[v0]"
    for i in range(1, n_images):
        # NEW OFFSET MATH
        # offset = i * (per_image - fade_duration)
        offset = i * (per_image - fade_dur)
        
        filter_parts.append(
            f"{last}[v{i}]"
            f"xfade=transition=fade:duration={fade_dur}:offset={offset:.3f}"
            f"[xf{i}]"
        )
        last = f"[xf{i}]"

    # Removed trim filter as requested. Use last[v] as input to subtitles
    
    sub_escaped = str(sub_path).replace("\\", "\\\\").replace(":", "\\:")
    
    # Premium Subtitle Styling: Montserrat Bold (fallback to Arial if missing, but naming it as requested)
    # White text (&H00FFFFFF), Black outline (&H00000000), Shadow, Bottom center (Alignment=2)
    # Added fade in/out for subtitles in force_style
    filter_parts.append(
        f"{last}subtitles={sub_escaped}:force_style="
        "'FontName=Montserrat Bold,FontSize=24,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=1,"
        "MarginV=40,Alignment=2,FadeV=200'[vout]"
    )

    filter_complex = ";".join(filter_parts)

    cmd = [
        "ffmpeg", "-y",
        *image_inputs,
        "-i", audio_file,
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", f"{n_images}:a",
        "-pix_fmt", "yuv420p",
        "-r", str(config.video_fps),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        str(VIDEO_DIR / "final_video.mp4")
    ]

    log.debug(f"FFmpeg filter complex: {filter_complex[:200]}...")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=max(120, int(total_duration * 4))
        )
        if result.returncode != 0:
            log.error(f"FFmpeg stderr: {result.stderr[-1000:]}")
            raise RuntimeError(f"FFmpeg failed (code {result.returncode})")

        output_file = VIDEO_DIR / "final_video.mp4"
        if output_file.exists():
            size_mb = output_file.stat().st_size / (1024 * 1024)
            log.info(f"Video created: final_video.mp4 ({size_mb:.1f}MB, {total_duration:.1f}s)")
            return str(output_file)
        else:
            raise RuntimeError("Output file was not created")

    except subprocess.TimeoutExpired:
        log.error("FFmpeg timed out")
        raise RuntimeError("FFmpeg timed out")
    except Exception:
        import traceback
        traceback.print_exc()
        raise