#!/usr/bin/env python3
import os
import sys
import time
import json
import argparse
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import config
from app.core.logger import setup_logging, setup_logging as _setup_logging
from app.utils.helpers import (
    DATA_DIR, IMAGES_DIR, AUDIO_DIR, VIDEO_DIR,
    CHECKPOINT_MANAGER, write_text, write_json, read_text
)

log = _setup_logging("pipeline")
log.setLevel("DEBUG")

PIPELINE_STEPS = [
    "topic",
    "script",
    "scenes",
    "images",
    "voice",
    "subtitles",
    "video",
]

STEP_DEPS = {
    "topic": [],
    "script": ["topic"],
    "scenes": ["script"],
    "images": ["scenes"],
    "voice": ["script"],
    "subtitles": ["script", "voice"],
    "video": ["images", "voice", "subtitles"],
}


def step_completed(step):
    ckpt = CHECKPOINT_MANAGER.get_last_checkpoint()
    if ckpt is None:
        return False
    try:
        return PIPELINE_STEPS.index(ckpt) >= PIPELINE_STEPS.index(step)
    except ValueError:
        return False


def mark_completed(step):
    if step == "video":
        CHECKPOINT_MANAGER.save_checkpoint("video")
    else:
        CHECKPOINT_MANAGER.save_checkpoint(step)


def run_step_topic(args):
    from app.scripting.topic_generator import select_topic

    topic = select_topic(topic_override=args.topic)
    write_text(DATA_DIR / "topic.txt", topic)
    mark_completed("topic")
    return topic


def run_step_script(args):
    from app.scripting.script_generator import generate_script

    topic = read_text(DATA_DIR / "topic.txt")
    script = generate_script(topic)
    write_text(DATA_DIR / "script.txt", script)
    mark_completed("script")
    return script


def run_step_scenes(args):
    from app.scripting.scene_planner import plan_scenes

    script = read_text(DATA_DIR / "script.txt")
    scenes = plan_scenes(script)
    write_json(DATA_DIR / "scenes.json", scenes)
    mark_completed("scenes")
    return scenes


def run_step_images(args):
    from app.media.image_generator import generate_images_batch

    scenes = json.loads(read_text(DATA_DIR / "scenes.json"))
    image_paths = generate_images_batch(scenes)
    if not any(p for p in image_paths if p):
        raise RuntimeError("No images generated")
    mark_completed("images")
    return image_paths


def run_step_voice(args):
    from app.media.voice_generator import generate_voice

    script = read_text(DATA_DIR / "script.txt")
    voice_file = generate_voice(script)
    mark_completed("voice")
    return voice_file


def run_step_subtitles(args):
    from app.video.subtitles import generate_subtitles

    script = read_text(DATA_DIR / "script.txt")
    voice_file = AUDIO_DIR / "voice.wav"
    sub_file = generate_subtitles(script, voice_file)
    mark_completed("subtitles")
    return sub_file


def run_step_video(args, voice_file, image_paths):
    from app.video.video_builder import build_video
    from app.media.music_mixer import mix_audio

    sub_file = VIDEO_DIR / "subtitles.srt"

    if args.music:
        log.info("Mixing background music...")
        voice_file = mix_audio(
            voice_file,
            music_file=args.music,
            voice_vol=config.get("voice_volume", 1.0),
            music_vol=config.get("music_volume", 0.2)
        )

    video_file = build_video(image_paths, voice_file, sub_file)
    mark_completed("video")
    return video_file


def run_upload_youtube(args):
    from app.distribution.youtube_upload import upload_video, generate_description, generate_tags

    video_path = VIDEO_DIR / "final_video.mp4"
    topic = read_text(DATA_DIR / "topic.txt") if (DATA_DIR / "topic.txt").exists() else args.topic or "AI Video"
    script = read_text(DATA_DIR / "script.txt") if (DATA_DIR / "script.txt").exists() else ""
    scenes = json.loads(read_text(DATA_DIR / "scenes.json")) if (DATA_DIR / "scenes.json").exists() else []

    title = args.title or f"{topic} - Amazing Facts"
    description = args.description or generate_description(topic, script, scenes)
    tags = generate_tags(topic)

    url = upload_video(str(video_path), title, description, tags)
    return url


def run_upload_instagram(args):
    from app.distribution.instagram_upload import upload_reel, generate_caption

    video_path = VIDEO_DIR / "final_video.mp4"
    topic = read_text(DATA_DIR / "topic.txt") if (DATA_DIR / "topic.txt").exists() else args.topic or "AI Video"
    script = read_text(DATA_DIR / "script.txt") if (DATA_DIR / "script.txt").exists() else ""

    caption = args.caption or generate_caption(topic, script)
    media_id = upload_reel(str(video_path), caption)
    return media_id


def run_full_pipeline(args):
    start_time = time.time()
    print("\n" + "=" * 60)
    print(" AI CONTENT PIPELINE - Starting")
    print("=" * 60)

    if args.clear:
        print("\n[CLEAR] Removing previous output files...")
        CHECKPOINT_MANAGER.clear()
        print("Done.\n")

    topic = None
    script = None
    scenes = None
    image_paths = None
    voice_file = None
    video_file = None

    if step_completed("topic") and not args.topic:
        log.info("Resuming from 'topic' step (using cached topic)")
        topic = read_text(DATA_DIR / "topic.txt")
        print(f"\n[Step 1] Topic: {topic}")
    else:
        print("\n[Step 1] Generating topic...")
        topic = run_step_topic(args)
        print(f"\n[Step 1] Selected: {topic}")

    if step_completed("script"):
        log.info("Resuming from 'script' step")
        script = read_text(DATA_DIR / "script.txt")
        print(f"\n[Step 2] Script loaded from cache ({len(script)} chars)")
    else:
        print("\n[Step 2] Generating script...")
        script = run_step_script(args)
        print(f"\n[Step 2] Script generated ({len(script)} chars)")

    if step_completed("scenes"):
        log.info("Resuming from 'scenes' step")
        scenes = json.loads(read_text(DATA_DIR / "scenes.json"))
        print(f"\n[Step 3] Scenes loaded: {len(scenes)} scenes")
    else:
        print("\n[Step 3] Parsing scenes...")
        scenes = run_step_scenes(args)
        print(f"\n[Step 3] Parsed {len(scenes)} scenes")

    if step_completed("images"):
        log.info("Resuming from 'images' step")
        manifest = json.loads((IMAGES_DIR / "manifest.json").read_text())
        image_paths = [
            IMAGES_DIR / f"scene_{i}.png"
            for i in range(len(scenes))
        ]
        image_paths = [str(p) if p.exists() else None for p in image_paths]
        valid = [p for p in image_paths if p]
        print(f"\n[Step 4] Images loaded: {len(valid)}/{len(scenes)} from cache")
        if len(valid) < len(scenes):
            print("  Some images missing, regenerating...")
            image_paths = run_step_images(args)
    else:
        print("\n[Step 4] Generating images...")
        image_paths = run_step_images(args)
        valid = [p for p in image_paths if p]
        print(f"\n[Step 4] Images generated: {len(valid)}/{len(scenes)}")

    if step_completed("voice"):
        log.info("Resuming from 'voice' step")
        voice_file = str(AUDIO_DIR / "voice.wav")
        print(f"\n[Step 5] Voice loaded from cache")
    else:
        print("\n[Step 5] Generating voice narration...")
        voice_file = run_step_voice(args)
        print(f"\n[Step 5] Voice generated: {voice_file}")

    if step_completed("subtitles"):
        log.info("Resuming from 'subtitles' step")
        print(f"\n[Step 6] Subtitles loaded from cache")
    else:
        print("\n[Step 6] Generating subtitles...")
        run_step_subtitles(args)
        print(f"\n[Step 6] Subtitles generated")

    print("\n[Step 7] Building final video...")
    video_file = run_step_video(args, voice_file, image_paths)

    elapsed = time.time() - start_time
    mins = int(elapsed // 60)
    secs = int(elapsed % 60)

    print("\n" + "=" * 60)
    print(" PIPELINE COMPLETE")
    print("=" * 60)
    print(f" Total time:  {mins}m {secs}s")
    print(f" Topic:       {topic}")
    print(f" Scenes:      {len(scenes)}")
    print(f" Video:       {video_file}")
    print(f" Size:        {Path(video_file).stat().st_size // (1024*1024)}MB")
    print("=" * 60)

    if args.upload:
        if args.upload == "youtube":
            print("\n[UPLOAD] Uploading to YouTube...")
            url = run_upload_youtube(args)
            print(f"[UPLOAD] YouTube: {url}")
        elif args.upload == "instagram":
            print("\n[UPLOAD] Uploading to Instagram...")
            media_id = run_upload_instagram(args)
            print(f"[UPLOAD] Instagram media_id: {media_id}")

    return video_file


def main():
    parser = argparse.ArgumentParser(description="AI Short-Video Pipeline")
    parser.add_argument("--topic", type=str, help="Force a specific topic")
    parser.add_argument("--upload", type=str, choices=["youtube", "instagram"], help="Upload to platform after generation")
    parser.add_argument("--resume", action="store_true", help="Resume from last checkpoint")
    parser.add_argument("--clear", action="store_true", help="Clear all output and start fresh")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--music", type=str, help="Path to background music file")
    parser.add_argument("--title", type=str, help="Custom video title for upload")
    parser.add_argument("--description", type=str, help="Custom video description for upload")
    parser.add_argument("--caption", type=str, help="Custom caption for Instagram")

    args = parser.parse_args()

    if args.debug:
        import logging
        log.setLevel(logging.DEBUG)
        for h in log.handlers:
            h.setLevel(logging.DEBUG)

    try:
        if args.resume:
            ckpt = CHECKPOINT_MANAGER.get_last_checkpoint()
            if ckpt:
                log.info(f"Resuming from checkpoint: {ckpt}")
            else:
                log.info("No checkpoint found, starting fresh")

        run_full_pipeline(args)

    except KeyboardInterrupt:
        print("\n\nPipeline interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n\nPIPELINE FAILED: {e}")
        if args.debug:
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()