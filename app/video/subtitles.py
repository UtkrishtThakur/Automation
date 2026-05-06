import os
import re
from pathlib import Path
from app.core.logger import setup_logging
from app.utils.helpers import VIDEO_DIR

log = setup_logging("subtitles")


def format_time(seconds):
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{hrs:02}:{mins:02}:{secs:02},{ms:03}"


def get_audio_duration(audio_file):
    import wave
    with wave.open(str(audio_file), "r") as f:
        frames = f.getnframes()
        rate = f.getframerate()
        return frames / float(rate)


def extract_voice_lines(script):
    voice_lines = []
    for line in script.splitlines():
        line = line.strip()
        if line.upper().startswith("VOICEOVER:"):
            text = line.split(":", 1)[1].strip()
            text = re.sub(r"\[.*?\]", "", text)
            text = re.sub(r"\(.*?\)", "", text)
            text = text.replace("*", "").replace("_", "").replace("#", "")
            text = re.sub(r"\s+", " ", text).strip()
            if text:
                voice_lines.append(text)
    return voice_lines


def chunk_text(text, max_words=8):
    words = text.split()
    chunks = []
    for i in range(0, len(words), max_words):
        chunk = " ".join(words[i:i + max_words])
        if chunk:
            chunks.append(chunk)
    return chunks


def generate_subtitles(script, audio_file):
    voice_lines = extract_voice_lines(script)
    if not voice_lines:
        raise RuntimeError("No VOICEOVER lines found")

    duration = get_audio_duration(audio_file)
    total_words = sum(len(line.split()) for line in voice_lines)

    if total_words == 0:
        raise RuntimeError("No words in VOICEOVER lines")

    time_per_word = duration / total_words

    sub_file = VIDEO_DIR / "subtitles.srt"

    with open(sub_file, "w", encoding="utf-8") as f:
        start = 0.0
        sub_index = 1

        for line in voice_lines:
            chunks = chunk_text(line, max_words=8)
            for chunk in chunks:
                chunk_words = len(chunk.split())
                chunk_duration = chunk_words * time_per_word
                end = start + chunk_duration

                f.write(f"{sub_index}\n")
                f.write(f"{format_time(start)} --> {format_time(end)}\n")
                f.write(f"{chunk}\n\n")

                start = end
                sub_index += 1

    log.info(f"Subtitles generated: {sub_index-1} subtitle blocks, {duration:.1f}s total")
    return str(sub_file)