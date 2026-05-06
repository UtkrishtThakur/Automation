import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

class Config:
    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance

    def _load(self):
        config_path = PROJECT_ROOT / "config.yaml"
        if config_path.exists():
            try:
                import yaml
                with open(config_path) as f:
                    self._config = yaml.safe_load(f) or {}
            except ImportError:
                self._config = {}
        else:
            self._config = {}

    def get(self, key, default=None):
        return self._config.get(key, default) if self._config else default

    @property
    def ollama_url(self):
        return os.getenv("OLLAMA_URL", self.get("ollama_url", "http://localhost:11434"))

    @property
    def ollama_model(self):
        return os.getenv("OLLAMA_MODEL", self.get("ollama_model", "qwen2.5:7b"))

    @property
    def hf_token(self):
        return os.getenv("HF_TOKEN", self.get("hf_token", ""))

    @property
    def youtube_client_id(self):
        return os.getenv("YOUTUBE_CLIENT_ID", self.get("youtube_client_id", ""))

    @property
    def youtube_client_secret(self):
        return os.getenv("YOUTUBE_CLIENT_SECRET", self.get("youtube_client_secret", ""))

    @property
    def instagram_access_token(self):
        return os.getenv("INSTAGRAM_ACCESS_TOKEN", self.get("instagram_access_token", ""))

    @property
    def output_dir(self):
        return os.getenv("OUTPUT_DIR", self.get("output_dir", "./data"))

    @property
    def voice_model(self):
        return os.getenv("VOICE_MODEL", self.get("voice_model", "models/voices/en_US-lessac-medium.onnx"))

    @property
    def video_width(self):
        return self.get("video_width", 1920)

    @property
    def video_height(self):
        return self.get("video_height", 1080)

    @property
    def video_fps(self):
        return self.get("video_fps", 30)

    @property
    def fade_duration(self):
        return self.get("fade_duration", 0.5)

    @property
    def max_retry(self):
        return self.get("max_retry", 5)

    @property
    def retry_delay(self):
        return self.get("retry_delay", 3)

config = Config()