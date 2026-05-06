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

    output_path = AUDIO_DIR / "voice.wav"

    log.info(f"Generating voice narration ({len(narration)} chars, ~{len(narration)//5}s)...")
    log.debug(f"Narration: {narration[:200]}...")

    model_path = VOICE_MODEL_PATH
    if not model_path.exists():
        raise RuntimeError(f"Voice model not found: {model_path}")

    try:
        result = subprocess.run(
            ["piper", "--model", str(model_path), "--output_file", str(output_path)],
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