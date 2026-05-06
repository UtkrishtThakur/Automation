import os
import subprocess
import random
import wave
from pathlib import Path
from app.core.config import config
from app.core.logger import setup_logging
from app.utils.helpers import VIDEO_DIR, IMAGES_DIR, get_audio_duration

log = setup_logging("video_builder")


def get_scale_effect(index, w=1920, h=1080):
    zoom_level = random.choice([1.0, 1.2, 1.5])
    scale_w = int(w * zoom_level)
    scale_h = int(h * zoom_level)
    crop_x = (scale_w - w) // 2
    crop_y = (scale_h - h) // 2
    return f"[{index}:v]scale={scale_w}:{scale_h},crop={w}:{h}:{crop_x}:{crop_y},setsar=1[v{index}]"


def get_ken_burns_effect(index, duration, width=1920, height=1080, fps=30):
    frames = int(duration * fps)

    direction = random.choice(["in", "out", "pan_left", "pan_right", "pan_up", "pan_down"])

    if direction == "in":
        start_scale, end_scale = 1.0, 1.4
        scale_expr = f"(1.0+0.4*(t/{duration}))"
    elif direction == "out":
        start_scale, end_scale = 1.4, 1.0
        scale_expr = f"(1.4-0.4*(t/{duration}))"
    elif direction == "pan_left":
        return (
            f"[{index}:v]scale=-2:{height+100},crop={width}:{height}:"
            f"'if(lt(t,{duration}),(t/{duration})*({width+100}-{width}),0)':0,setsar=1[v{index}]"
        )
    elif direction == "pan_right":
        return (
            f"[{index}:v]scale=-2:{height+100},crop={width}:{height}:"
            f"'if(lt(t,{duration}),({width+100}-{width})-(t/{duration})*({width+100}-{width}),0)':0,setsar=1[v{index}]"
        )
    elif direction == "pan_up":
        return (
            f"[{index}:v]scale={width+100}:-2,crop={width}:{height}:"
            f"0:'if(lt(t,{duration}),(t/{duration})*({height+100}-{height}),0)',setsar=1[v{index}]"
        )
    elif direction == "pan_down":
        return (
            f"[{index}:v]scale={width+100}:-2,crop={width}:{height}:"
            f"0:'if(lt(t,{duration}),({height+100}-{height})-(t/{duration})*({height+100}-{height}),0)',setsar=1[v{index}]"
        )

    return (
        f"[{index}:v]scale={int(width*1.4)}:{int(height*1.4)},crop={width}:{height}:"
        f"'iw/2-(iw/{scale_expr})/2':'ih/2-(ih/{scale_expr})/2',setsar=1[v{index}]"
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
    per_image = total_duration / n_images
    fade_dur = config.fade_duration

    log.info(f"Building video: {n_images} scenes, {total_duration:.1f}s total, {fade_dur}s fades")

    image_inputs = []
    for img in image_paths:
        image_inputs.extend(["-loop", "1", "-t", str(per_image), "-i", img])

    filter_parts = []

    for i in range(n_images):
        effect = get_ken_burns_effect(i, per_image, config.video_width, config.video_height, config.video_fps)
        filter_parts.append(effect)

    last = "[v0]"
    for i in range(1, n_images):
        offset = per_image * i - fade_dur / 2
        if offset < 0:
            offset = 0.0
        filter_parts.append(
            f"{last}[v{i}]"
            f"xfade=transition=fade:duration={fade_dur}:offset={offset:.3f}"
            f"[xf{i}]"
        )
        last = f"[xf{i}]"

    filter_parts.append(f"{last}trim=duration={total_duration}[vtrim];[vtrim]setsar=1[vtrim2]")
    last = "[vtrim2]"

    sub_escaped = sub_path.replace("\\", "\\\\")
    filter_parts.append(
        f"{last}subtitles={sub_escaped}:force_style="
        "'FontName=Arial Bold,FontSize=26,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,BorderStyle=1,Outline=2.5,Shadow=0,"
        "MarginV=50,Alignment=2'[vout]"
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
        raise RuntimeError("FFmpeg timed out")
    except Exception as e:
        raise RuntimeError(f"Video build failed: {e}")