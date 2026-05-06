import os
import wave
import re

OUTPUT_DIR = "data/video"
SUB_FILE = f"{OUTPUT_DIR}/subtitles.srt"

os.makedirs(OUTPUT_DIR, exist_ok=True)


def get_audio_duration(audio_file):

    with wave.open(audio_file, "r") as f:
        frames = f.getnframes()
        rate = f.getframerate()
        duration = frames / float(rate)

    return duration


def format_time(seconds):

    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)

    return f"{hrs:02}:{mins:02}:{secs:02},{ms:03}"


def extract_voice_lines(script):

    voice_lines = []

    for line in script.splitlines():
        line = line.strip()

        if line.upper().startswith("VOICEOVER:"):
            text = line.split(":", 1)[1].strip()
            
            # Clean matching the voice generator
            text = re.sub(r"\[.*?\]", "", text)
            text = re.sub(r"\(.*?\)", "", text)
            text = text.replace("*", "").replace("_", "").replace("#", "")
            text = re.sub(r"\s+", " ", text).strip()
            
            if text:
                voice_lines.append(text)

    return voice_lines


def chunk_text(text, max_words=6):
    """
    Split a long line into smaller chunks of words, typically 6-8 words max.
    This creates karaoke-style dynamic subtitles.
    """
    words = text.split()
    chunks = []
    
    for i in range(0, len(words), max_words):
        chunks.append(" ".join(words[i:i + max_words]))
        
    return chunks


def generate_subtitles(script, audio_file):

    voice_lines = extract_voice_lines(script)

    if not voice_lines:
        raise RuntimeError("No VOICEOVER lines found")

    duration = get_audio_duration(audio_file)
    
    # Calculate words to distribute duration proportionally
    total_words = sum(len(line.split()) for line in voice_lines)
    time_per_word = duration / total_words if total_words > 0 else 0

    with open(SUB_FILE, "w") as f:

        start = 0
        sub_index = 1

        for line in voice_lines:
            
            chunks = chunk_text(line, max_words=6)
            
            for chunk in chunks:
                chunk_words = len(chunk.split())
                chunk_duration = chunk_words * time_per_word
                end = start + chunk_duration

                f.write(f"{sub_index}\n")
                f.write(f"{format_time(start)} --> {format_time(end)}\n")
                f.write(chunk + "\n\n")

                start = end
                sub_index += 1

    print("Subtitles created →", SUB_FILE)

    return SUB_FILE