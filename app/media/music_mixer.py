import subprocess
import random
import os
from pathlib import Path
from app.core.logger import setup_logging
from app.utils.helpers import AUDIO_DIR, VIDEO_DIR, get_audio_duration

log = setup_logging("music")


MUSIC_DIR = Path("data/music")
MUSIC_DIR.mkdir(exist_ok=True)

MUSIC_SEARCH_PROMPT = (
    "royalty free ambient cinematic background music, "
    "no vocals, relaxing, educational video score"
)


def generate_background_music(topic, duration):
    log.warning("Background music generation requires external API integration (Audiospark, Mubert, etc.)")
    log.info("Skipping music — using voice-only track")
    return None


def mix_audio(voice_file, music_file=None, voice_vol=1.0, music_vol=0.15):
    voice_dur = get_audio_duration(voice_file)

    if not music_file or not os.path.exists(music_file):
        log.info("No music file, copying voice as final audio")
        import shutil
        final = AUDIO_DIR / "final_audio.wav"
        shutil.copy2(voice_file, final)
        return str(final)

    # Ducking parameters
    duck_vol = music_vol * 0.4
    fade_dur = 0.5

    mixed = AUDIO_DIR / "mixed_audio.wav"

    # FFmpeg filter for looping music, fading it in/out, and ducking during voice
    # We use sidechain compress or simple volume manipulation if we know the voice timing
    # Since amix is used, we'll try a simpler approach with volume filters
    
    cmd = [
        "ffmpeg", "-y",
        "-i", voice_file,
        "-stream_loop", "-1", "-i", music_file,
        "-filter_complex",
        f"[1:a]trim=duration={voice_dur},volume={music_vol},"
        f"afade=t=in:st=0:d={fade_dur},afade=t=out:st={voice_dur-fade_dur}:d={fade_dur}[bg];"
        f"[0:a]volume={voice_vol}[fg];"
        f"[fg][bg]amix=inputs=2:duration=first:dropout_transition=0",
        "-ar", "44100",
        "-ac", "2",
        str(mixed)
    ]

    try:
        subprocess.run(cmd, capture_output=True, check=True, timeout=60)
        log.info(f"Mixed audio created with fading: {mixed}")
        return str(mixed)
    except subprocess.CalledProcessError as e:
        log.error(f"Audio mix failed: {e.stderr.decode()[-300:]}")
        return voice_file