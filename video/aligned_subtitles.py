import whisperx
import os

OUTPUT_DIR = "/mnt/ai/Projects/Automation/data/video"
SUB_FILE = f"{OUTPUT_DIR}/subtitles.srt"

os.makedirs(OUTPUT_DIR, exist_ok=True)


def format_time(seconds):

    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)

    return f"{hrs:02}:{mins:02}:{secs:02},{ms:03}"


def generate_aligned_subtitles(audio_file):

    print("Running speech alignment...")

    model = whisperx.load_model("base", device="cpu")

    result = model.transcribe(audio_file)

    segments = result["segments"]

    with open(SUB_FILE, "w") as f:

        for i, seg in enumerate(segments):

            start = format_time(seg["start"])
            end = format_time(seg["end"])

            text = seg["text"].strip()

            f.write(f"{i+1}\n")
            f.write(f"{start} --> {end}\n")
            f.write(text + "\n\n")

    print("Aligned subtitles created →", SUB_FILE)

    return SUB_FILE