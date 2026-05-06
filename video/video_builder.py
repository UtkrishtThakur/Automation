import os
import subprocess
import wave
import random

OUTPUT_DIR = "data/video"
OUTPUT_VIDEO = f"{OUTPUT_DIR}/final_video.mp4"
SUB_FILE = f"{OUTPUT_DIR}/subtitles.srt"

os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_audio_duration(audio_file):

    with wave.open(audio_file, "r") as f:
        frames = f.getnframes()
        rate = f.getframerate()
        duration = frames / float(rate)

    return duration


def motion_filter(index, duration):
    
    # Required frames for this specific zoompan duration
    frames = int(duration * 30)
    
    # Ensure images are scaled and padded properly to 1920x1080 before motion
    base_scale = f"[{index}:v]scale=-2:1080,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1[vpad{index}];"
    
    effects = [

        # zoom in
        f"[vpad{index}]zoompan=z='min(zoom+0.0015,1.5)':"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:fps=30[v{index}]",

        # zoom out
        f"[vpad{index}]zoompan=z='max(zoom-0.0015,1.0)':"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:fps=30[v{index}]",

        # pan left (requires larger source before crop, so we scale larger then crop)
        f"[{index}:v]scale=-2:1200,pad=2400:1200:(ow-iw)/2:(oh-ih)/2,crop=1920:1080:"
        f"x='(n/{frames})*(2400-1920)':y=60,fps=30[v{index}]",

        # pan right
        f"[{index}:v]scale=-2:1200,pad=2400:1200:(ow-iw)/2:(oh-ih)/2,crop=1920:1080:"
        f"x='(2400-1920)-(n/{frames})*(2400-1920)':y=60,fps=30[v{index}]",

        # gentle rotation
        f"[vpad{index}]rotate=0.02*sin(PI*n/{frames}):"
        f"c=black@0,fps=30[v{index}]"
    ]

    effect = random.choice(effects)
    
    # If using pad base scale, ensure we return both parts
    if effect.startswith("[vpad"):
        return base_scale + effect
    
    return effect


def build_video(images, audio_file):

    print("Building cinematic video with motion effects...")

    if not images:
        raise RuntimeError("No images provided")

    if not os.path.exists(audio_file):
        raise RuntimeError("Audio file missing")

    if not os.path.exists(SUB_FILE):
        raise RuntimeError("Subtitle file missing")

    total_duration = get_audio_duration(audio_file)
    per_image = total_duration / len(images)
    
    # Add transition overlap duration (0.5s fade means we need 0.5s extra footage per image except last)
    fade_duration = 0.5
    image_display_time = per_image + fade_duration

    image_inputs = []
    filter_parts = []

    # load images
    for img in images:
        image_inputs.extend(["-loop", "1", "-t", str(image_display_time), "-i", img])

    # motion effect per image
    for i in range(len(images)):
        filter_parts.append(motion_filter(i, image_display_time))

    # crossfade chain
    last = "[v0]"

    for i in range(1, len(images)):

        # Offset is exactly per_image * i
        offset = per_image * i

        filter_parts.append(
            f"{last}[v{i}]"
            f"xfade=transition=fade:duration={fade_duration}:offset={offset}"
            f"[xf{i}]"
        )

        last = f"[xf{i}]"

    # Ensure final duration matches audio exactly
    filter_parts.append(f"{last}trim=duration={total_duration}[vtrim]")
    last = "[vtrim]"

    # subtitles - improved styling (thick outline, modern font settings)
    filter_parts.append(
        f"{last}subtitles={SUB_FILE}:force_style='FontName=Arial,"
        f"FontSize=24,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
        f"BorderStyle=1,Outline=2.5,Shadow=0,MarginV=40,Alignment=2,Bold=1'[vout]"
    )

    cmd = [
        "ffmpeg",
        "-y",
        *image_inputs,
        "-i",
        audio_file,
        "-filter_complex",
        ";".join(filter_parts),
        "-map",
        "[vout]",
        "-map",
        f"{len(images)}:a",
        "-pix_fmt",
        "yuv420p",
        "-r",
        "30",
        "-video_track_timescale", "30000",
        OUTPUT_VIDEO
    ]
    
    print("\nExecuting FFmpeg command...")
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print("\nFFMPEG Error:")
        print(e.stderr.decode("utf-8")[-1000:])
        raise

    print("Video created →", OUTPUT_VIDEO)

    return OUTPUT_VIDEO