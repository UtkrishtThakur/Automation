import os
import json
import wave
import time as time_module
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"

DATA_DIR = Path(os.getenv("OUTPUT_DIR", str(DEFAULT_DATA_DIR))).resolve()
IMAGES_DIR = DATA_DIR / "images"
AUDIO_DIR = DATA_DIR / "audio"
VIDEO_DIR = DATA_DIR / "video"
MODELS_DIR = PROJECT_ROOT / "models"
VOICE_MODEL_PATH = PROJECT_ROOT / os.getenv("VOICE_MODEL", "models/voices/en_US-lessac-medium.onnx")

for d in [DATA_DIR, IMAGES_DIR, AUDIO_DIR, VIDEO_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def get_audio_duration(audio_file):
    with wave.open(str(audio_file), "r") as f:
        frames = f.getnframes()
        rate = f.getframerate()
        return frames / float(rate)


def read_json(path):
    with open(path) as f:
        return json.load(f)


def write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def read_text(path):
    with open(path) as f:
        return f.read().strip()


def write_text(path, text):
    with open(path, "w") as f:
        f.write(text)


class CheckpointManager:
    def __init__(self, data_dir=None):
        self.data_dir = Path(data_dir or DATA_DIR)

    def save_checkpoint(self, step_name):
        manifest = self.data_dir / "images" / "manifest.json"
        meta = {}
        if manifest.exists():
            try:
                meta = json.loads(manifest.read_text())
            except:
                pass
        meta["last_checkpoint"] = step_name
        meta["timestamp"] = time_module.time()
        manifest.write_text(json.dumps(meta, indent=2))

        checkpoint_file = self.data_dir / ".checkpoint"
        checkpoint_file.write_text(step_name)

    def get_last_checkpoint(self):
        checkpoint_file = self.data_dir / ".checkpoint"
        if checkpoint_file.exists():
            return checkpoint_file.read_text().strip()
        return None

    def is_complete(self):
        return (self.data_dir / "video" / "final_video.mp4").exists()

    def clear(self):
        for item in self.data_dir.rglob("*"):
            if item.is_file() and item.name not in [".gitkeep"]:
                try:
                    item.unlink()
                except:
                    pass

CHECKPOINT_MANAGER = CheckpointManager()