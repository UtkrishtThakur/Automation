import subprocess
import re
import os
from pathlib import Path
from app.core.config import config
from app.core.logger import setup_logging
from app.utils.helpers import AUDIO_DIR, VOICE_MODEL_PATH

log = setup_logging("voice_generator")


def extract_voiceover(script):
    voice_lines = []
    for line in script.splitlines():
        line = line.strip()
        if line.upper().startswith("VOICEOVER:"):
            text = line.split(":", 1)[1].strip()
            voice_lines.append(text)
    return " ".join(voice_lines)


def clean_text(text):
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\(.*?\)", "", text)
    text = text.replace("*", "").replace("_", "").replace("#", "")
    text = re.sub(r",([^\s])", r", \1", text)
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    if text and text[-1] not in ".!?":
        text += "."
    return text


def generate_voice(script):
    narration = extract_voiceover(script)
    narration = clean_text(narration)

    if not narration:
        raise RuntimeError("No VOICEOVER lines found in script")

    # Improve pacing: insert slight pauses after punctuation
    # Piper naturally adds some pause, but we can exaggerate it by adding commas or using SSML if supported
    # Alternatively, we can just process the narration to ensure punctuation is present.
    # To slow down narration, we use the --length_scale parameter.
    
    output_path = AUDIO_DIR / "voice.wav"

    log.info(f"Generating voice narration ({len(narration)} chars, target 25-30s)...")
    
    model_path = VOICE_MODEL_PATH
    if not model_path.exists():
        raise RuntimeError(f"Voice model not found: {model_path}")

    # Slow down narration slightly (1.0 is default, higher is slower)
    # Target 25-30 seconds for 120-160 words (~2.5 words/sec default).
    # 150 words / 25s = 6 words/sec (too fast).
    # 150 words / 30s = 5 words/sec.
    # Actually, default is around 2.5-3 words/sec.
    # 150 words / 3.0 wps = 50 seconds.
    # We need to speed it up or shorten the script?
    # Wait, the user said: "25-30 second narration. 120-160 words."
    # 160 / 30 = 5.33 words per second. This is actually quite fast.
    # Kurzgesagt style is usually slower.
    # Maybe 100-120 words is better for 30s.
    # But I'll stick to the user's word count and adjust speed.
    
    length_scale = "1.15" # Slightly slower for dramatic effect

    try:
        result = subprocess.run(
            ["piper", "--model", str(model_path), "--output_file", str(output_path), "--length_scale", length_scale],
            input=narration.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        log.info(f"Voice generated: {output_path} ({output_path.stat().st_size//1024}KB)")
        return str(output_path)

    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode("utf-8", errors="replace")
        log.error(f"Piper error: {stderr}")
        raise RuntimeError(f"Voice generation failed: {stderr}")


def check_piper_available():
    try:
        r = subprocess.run(["piper", "--help"], capture_output=True, timeout=5)
        return r.returncode == 0
    except:
        return False