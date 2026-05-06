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


def mix_audio(voice_file, music_file=None, voice_vol=1.0, music_vol=0.2):
    voice_dur = get_audio_duration(voice_file)

    if not music_file or not os.path.exists(music_file):
        log.info("No music file, copying voice as final audio")
        import shutil
        final = AUDIO_DIR / "final_audio.wav"
        shutil.copy2(voice_file, final)
        return str(final)

    music_dur = get_audio_duration(music_file)

    voice_vol_linear = str(voice_vol)
    music_vol_linear = str(music_vol)

    loop_music = music_dur < voice_dur
    music_input = ["-stream_loop", "-1"] if loop_music else []
    music_trim = f"if(lt(t,{voice_dur}),t,0)" if loop_music else f"0:{voice_dur}"

    mixed = AUDIO_DIR / "mixed_audio.wav"

    cmd = [
        "ffmpeg", "-y",
        "-i", voice_file,
        "-i", music_file,
        *music_input,
        "-filter_complex",
        f"[1:a]atrim={music_trim},volume={music_vol_linear}[music];"
        f"[0:a]volume={voice_vol_linear}[voice];"
        f"[voice][music]amix=inputs=2:duration=first:dropout_transition=0[dout]",
        "-map", "[dout]",
        "-ar", "44100",
        "-ac", "2",
        str(mixed)
    ]

    try:
        subprocess.run(cmd, capture_output=True, check=True, timeout=60)
        log.info(f"Mixed audio created: {mixed}")
        return str(mixed)
    except subprocess.CalledProcessError as e:
        log.error(f"Audio mix failed: {e.stderr.decode()[-300:]}")
        return voice_file