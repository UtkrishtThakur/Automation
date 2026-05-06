# AI Short-Video Factory

Automated pipeline that generates complete short-form educational videos (45–90s) from a single command — inspired by Kurzgesagt / Veritasium style.

```
Topic → Script → Scenes → Images + Voice → Subtitles → Video → Upload
```

---

## Features

- **Topic generation** — Ollama-powered educational topic selection
- **Script generation** — 5-scene structured narration script
- **Image generation** — HuggingFace FLUX.1-schnell with cinematic prompts
- **Voice synthesis** — Piper TTS with local ONNX model
- **Karaoke subtitles** — Word-proportional timing
- **Cinematic video** — Ken Burns effects, crossfades, styled subtitles
- **Background music** — Optional audio mixing
- **Auto-upload** — YouTube Data API v3, Instagram Graph API
- **Resume mode** — Continue from last checkpoint on failure
- **Config system** — `config.yaml` + environment variables

---

## Quick Start

```bash
# 1. Start Ollama (in a separate terminal)
ollama pull qwen2.5:7b
ollama serve

# 2. Copy and configure environment
cp .env.example .env
# Edit .env — set HF_TOKEN from https://huggingface.co/settings/tokens

# 3. Build and run with Docker (recommended)
docker compose up --build

# Or run locally
pip install -r requirements.txt
python run_pipeline.py
```

---

## CLI Usage

```bash
# Full pipeline — AI picks a topic
python run_pipeline.py

# With a specific topic
python run_pipeline.py --topic "Why black holes are invisible"

# Resume from last checkpoint
python run_pipeline.py --resume

# Start fresh (clear all output)
python run_pipeline.py --clear

# Generate and upload to YouTube
python run_pipeline.py --upload youtube

# Generate with custom YouTube metadata
python run_pipeline.py --topic "Quantum entanglement" \
  --title "The strangest connection in physics" \
  --description "What Einstein called 'spooky action at a distance'" \
  --upload youtube

# Debug logging
python run_pipeline.py --debug

# With background music
python run_pipeline.py --music ./data/music/ambient.mp3
```

---

## Configuration

### Environment Variables (`.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_URL` | Ollama API endpoint | `http://localhost:11434` |
| `OLLAMA_MODEL` | Ollama model name | `qwen2.5:7b` |
| `HF_TOKEN` | HuggingFace API token | *required* |
| `YOUTUBE_CLIENT_ID` | YouTube OAuth client ID | — |
| `YOUTUBE_CLIENT_SECRET` | YouTube OAuth client secret | — |
| `INSTAGRAM_ACCESS_TOKEN` | Instagram/Meta access token | — |
| `OUTPUT_DIR` | Output directory | `./data` |

### Config File (`config.yaml`)

```yaml
ollama_url: http://localhost:11434
ollama_model: qwen2.5:7b
video_width: 1920
video_height: 1080
video_fps: 30
fade_duration: 0.5
max_retry: 5
retry_delay: 3
voice_volume: 1.0
music_volume: 0.2
```

---

## Makefile Commands

```bash
make build    # Build Docker image
make run      # Run pipeline in container
make run-detach  # Run in background
make logs     # Tail container logs
make shell    # Open shell in container
make clean    # Remove all output files
make resume   # Resume from last checkpoint
make debug    # Run with debug output
make test     # Verify all Python imports
make lint     # Syntax check all modules
```

---

## Architecture

```
run_pipeline.py          # CLI orchestrator
├── app/
│   ├── core/
│   │   ├── config.py    # Config loading (yaml + env)
│   │   └── logger.py    # Structured logging
│   ├── scripting/
│   │   ├── topic_generator.py    # Ollama topic selection
│   │   ├── script_generator.py   # Ollama script generation
│   │   └── scene_planner.py      # Regex scene parser
│   ├── media/
│   │   ├── image_generator.py    # HuggingFace FLUX image gen
│   │   ├── voice_generator.py   # Piper TTS synthesis
│   │   └── music_mixer.py       # FFmpeg audio mixing
│   ├── video/
│   │   ├── subtitles.py          # SRT subtitle generation
│   │   └── video_builder.py      # FFmpeg video compositor
│   ├── distribution/
│   │   ├── youtube_upload.py     # YouTube Data API v3
│   │   └── instagram_upload.py  # Instagram Graph API
│   └── utils/
│       └── helpers.py            # File I/O, checkpoints
├── config.yaml
├── Dockerfile
└── docker-compose.yml
```

### Pipeline Flow

```
Step 1: Topic        select_topic()      → data/topic.txt
Step 2: Script       generate_script()   → data/script.txt
Step 3: Scenes       plan_scenes()      → data/scenes.json
Step 4: Images       generate_images()  → data/images/scene_*.png
Step 5: Voice        generate_voice()   → data/audio/voice.wav
Step 6: Subtitles    generate_subtitles() → data/video/subtitles.srt
Step 7: Video        build_video()      → data/video/final_video.mp4
```

---

## Output Files

```
data/
├── topic.txt              ← Selected topic
├── script.txt             ← Full 5-scene script
├── scenes.json            ← Parsed scene objects
├── images/
│   ├── scene_0.png
│   ├── scene_1.png
│   ├── scene_2.png
│   ├── scene_3.png
│   ├── scene_4.png
│   └── manifest.json      ← Image generation manifest
├── audio/
│   ├── voice.wav          ← TTS narration
│   └── mixed_audio.wav    ← Voice + music (if used)
└── video/
    ├── subtitles.srt      ← Karaoke-style subtitles
    └── final_video.mp4    ← Final 1080p/30fps video
```

---

## External Dependencies

| Service | Purpose | Setup |
|---------|---------|-------|
| **Ollama** (`qwen2.5:7b`) | Topic + script generation | `ollama pull qwen2.5:7b` |
| **HuggingFace** (FLUX.1-schnell) | Image generation | Get token at huggingface.co |
| **Piper TTS** | Voice synthesis | Bundled ONNX model + binary |
| **FFmpeg** | Video composition | System package |
| **YouTube Data API v3** | YouTube upload | Google Cloud Console |
| **Instagram Graph API** | Instagram upload | Meta Developer Console |

---

## Troubleshooting

### Ollama connection errors
```bash
# Verify Ollama is running
curl http://localhost:11434/api/tags
# If using Docker, use host.docker.internal
export OLLAMA_URL=http://host.docker.internal:11434
```

### HF_TOKEN invalid
```bash
# Test your token
curl https://huggingface.co/api/whoami-v2 \
  -H "Authorization: Bearer $HF_TOKEN"
```

### Piper TTS not found
```bash
# Install piper binary
curl -fsSL https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_linux_amd64.tar.gz \
  | tar xz -C /usr/local/bin
```

### FFmpeg errors in video build
```bash
# Verify FFmpeg has all codecs
ffmpeg -formats | grep yuv420p
ffmpeg -filters | grep zoompan
```

### Image generation fails
- Check HF_TOKEN has Inference API access
- FLUX.1-schnell has rate limits — increase `retry_delay` in config
- Images are cached — use `--clear` to regenerate

### Pipeline fails mid-run
```bash
# Resume from last successful step
python run_pipeline.py --resume
```

---

## Development

```bash
# Local development
pip install -r requirements.txt
python run_pipeline.py --debug

# Test without Ollama/HF (dry-run logic)
python -c "
from app.scripting.scene_planner import plan_scenes
scenes = plan_scenes('SCENE 1\nVISUAL: test\nVOICEOVER: test\n'*5)
print(len(scenes), 'scenes')
"

# Run in Docker with local code changes
docker compose up --build
```

---

## API Keys Required

1. **HuggingFace** (required) — https://huggingface.co/settings/tokens
   - Enable "Read" permissions for Inference API

2. **YouTube** (optional) — https://console.cloud.google.com/apis/credentials
   - Create OAuth 2.0 Client ID (Desktop app)
   - Enable YouTube Data API v3

3. **Instagram** (optional) — https://developers.facebook.com
   - Create Meta app with Instagram Graph API
   - Get User Access Token with `instagram_content_publish` permission