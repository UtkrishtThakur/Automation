import os
import subprocess
import re

OUTPUT_DIR = "data/audio"
VOICE_MODEL = "models/voices/en_US-lessac-medium.onnx"

os.makedirs(OUTPUT_DIR, exist_ok=True)


def extract_voiceover(script):
    """
    Extract VOICEOVER lines from structured script.
    """

    voice_lines = []

    for line in script.splitlines():

        line = line.strip()

        if line.upper().startswith("VOICEOVER:"):
            voice_lines.append(line.split(":", 1)[1].strip())

    narration = " ".join(voice_lines)

    return narration


def clean_text(text):
    """
    Clean narration text for TTS.
    Removes stage directions, markdown, and normalizes punctuation for better pacing.
    """

    # Remove text in brackets or parentheses (usually stage directions)
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\(.*?\)", "", text)

    # Remove markdown formatters
    text = text.replace("*", "")
    text = text.replace("_", "")
    text = text.replace("#", "")

    # Ensure commas have space after them for pacing
    text = re.sub(r",([^\s])", r", \1", text)

    # Normalize multiple spaces
    text = re.sub(r"\s+", " ", text)

    # Ensure it ends with punctuation
    text = text.strip()
    if text and not text[-1] in ".!?":
        text += "."

    return text


def generate_voice(script):

    narration = extract_voiceover(script)
    narration = clean_text(narration)

    if not narration:
        raise RuntimeError("No VOICEOVER lines found in script")

    output_path = os.path.join(OUTPUT_DIR, "voice.wav")

    print("\nNarration sent to Piper:\n")
    print(narration)

    try:

        subprocess.run(
            [
                "piper",
                "--model",
                VOICE_MODEL,
                "--output_file",
                output_path
            ],
            input=narration.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )

        print(f"\nVoice generated → {output_path}")

        return output_path

    except subprocess.CalledProcessError as e:

        print("\nPiper error:")
        print(e.stderr.decode())

        raise RuntimeError("Voice generation failed")