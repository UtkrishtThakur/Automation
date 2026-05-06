# AI Video Content Pipeline

Fully automated text-to-video generation system that produces short-form educational videos (45–90 seconds) in the style of Kurzgesagt / Veritasium — from topic idea to finished MP4, zero human input.

---

## End Goal

**One command (`python run_pipeline.py`) generates a complete, publish-ready video:**
- AI-picked educational topic
- 5-scene narrated script
- Cinematic AI-generated images with Ken Burns motion
- Natural TTS voiceover
- Karaoke-style subtitles
- Cross-faded 1080p video with audio sync
- *(Planned)* Auto-upload to YouTube & Instagram

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────────────┐
│                      run_pipeline.py                           │
│                    (Orchestrator — 7 steps)                     │
└──────┬─────────┬──────────┬──────────┬──────────┬──────────────┘
       │         │          │          │          │
       ▼         ▼          ▼          ▼          ▼
  ┌─────────┐ ┌──────────┐ ┌────────┐ ┌────────┐ ┌─────────────┐
  │scripting│ │  media   │ │ video  │ │ models │ │distribution │
  │         │ │          │ │        │ │        │ │  (planned)  │
  └─────────┘ └──────────┘ └────────┘ └────────┘ └─────────────┘
```

### Pipeline Flow

```
Topic → Script → Scenes → Images + Voice → Subtitles → Video
  1       2        3         4      5          6          7
```

| Step | Module | Function | What it does |
|------|--------|----------|-------------|
| 1 | `scripting/topic_generator.py` | `select_topic()` | Asks Ollama to generate 5 topics, picks one at random |
| 2 | `scripting/script_generator.py` | `generate_script(topic)` | Ollama generates a 5-scene VISUAL/VOICEOVER script |
| 3 | `scripting/scene_planner.py` | `plan_scenes(script)` | Deterministic parser — extracts scenes, builds image prompts |
| 4 | `media/image_generator.py` | `generate_image(prompt, i)` | HuggingFace FLUX.1-schnell generates a PNG per scene |
| 5 | `media/voice_generator.py` | `generate_voice(script)` | Piper TTS synthesizes narration to WAV |
| 6 | `video/subtitles.py` | `generate_subtitles(script, audio)` | Word-proportional SRT subtitle generation |
| 7 | `video/video_builder.py` | `build_video(images, audio)` | FFmpeg composites everything into 1080p/30fps MP4 |

---

## Module Details

### `scripting/` — Content Generation (Ollama)

**LLM:** `qwen2.5:7b` via Ollama REST API (`/api/generate`)

- **topic_generator.py** — Prompts the LLM for 5 curiosity-driven educational topics, parses the numbered list, randomly selects one. Falls back to a hardcoded topic if parsing fails.
- **script_generator.py** — Sends a detailed system prompt demanding exactly 5 scenes in `SCENE N / VISUAL: / VOICEOVER:` format. Cleans markdown artifacts, validates ≥5 visual + voiceover lines.
- **scene_planner.py** — Pure regex parser (no LLM call). Extracts VISUAL/VOICEOVER pairs, appends cinematic suffix to each visual description for image generation prompts.

### `media/` — Asset Generation

- **image_generator.py** — Calls HuggingFace Inference API (`FLUX.1-schnell` model). Simplifies prompts to 120 chars, retries up to 5× with 3s backoff. Saves PNGs to `data/images/`.
- **voice_generator.py** — Extracts all VOICEOVER lines, concatenates them, cleans stage directions/markdown, pipes to **Piper TTS** (`en_US-lessac-medium` ONNX model) via subprocess. Outputs `data/audio/voice.wav`.

### `video/` — Assembly

- **subtitles.py** — Splits narration into 6-word chunks (karaoke-style). Distributes timing proportionally by word count across the audio duration. Outputs `data/video/subtitles.srt`.
- **aligned_subtitles.py** — *(Alternative, unused in pipeline)* Uses WhisperX for speech-aligned subtitle generation. Available as an upgrade path for more accurate timing.
- **video_builder.py** — The core compositor:
  - Distributes audio duration equally across images
  - Applies random Ken Burns effects per scene (zoom in/out, pan L/R, gentle rotation)
  - Chains `xfade` transitions (0.5s fades) between scenes
  - Burns SRT subtitles with styled text (Arial Bold, white with black outline)
  - Outputs `data/video/final_video.mp4` at 1920×1080, 30fps

### `distribution/` — Upload (Stubbed)

- `youtube_upload.py` — Empty, planned
- `instagram_upload.py` — Empty, planned

### `models/` — Local Model Files

- `voices/en_US-lessac-medium.onnx` — Piper TTS voice model (~60MB)

---

## Data Flow & File Outputs

```
data/
├── topic.txt              ← Selected topic string
├── script.txt             ← Full 5-scene script
├── scenes.json            ← Parsed scene objects with prompts
├── images/
│   ├── scene_0.png        ← Generated image per scene
│   ├── scene_1.png
│   ├── scene_2.png
│   ├── scene_3.png
│   └── scene_4.png
├── audio/
│   └── voice.wav          ← TTS narration
└── video/
    ├── subtitles.srt      ← Karaoke-style subtitles
    └── final_video.mp4    ← Final output
```

---

## External Dependencies

| Dependency | Purpose | How it connects |
|------------|---------|-----------------|
| **Ollama** (`qwen2.5:7b`) | Topic + script generation | REST API at `OLLAMA_URL` (default `localhost:11434`) |
| **HuggingFace Inference** (FLUX.1-schnell) | Image generation | HTTPS API, auth via `HF_TOKEN` env var |
| **Piper TTS** | Voice synthesis | Local binary, uses ONNX model in `models/voices/` |
| **FFmpeg** | Video composition | System binary, called via subprocess |

---

## Infrastructure

- **Docker** — `python:3.11-slim` base with `ffmpeg` + `libsndfile1`
- **docker-compose** — Mounts project as volume, passes `HF_TOKEN` from `.env`, connects to host Ollama via `host.docker.internal`
- **Environment variables:**
  - `OLLAMA_URL` — Ollama endpoint (defaults to `http://localhost:11434`)
  - `HF_TOKEN` — HuggingFace API token for image generation

---

## How to Run

```bash
# Ensure Ollama is running with qwen2.5:7b
ollama pull qwen2.5:7b
ollama serve

# Option A: Docker (recommended)
docker compose up --build

# Option B: Local
pip install -r requirements.txt
python run_pipeline.py
```

---

## What's Built vs. What's Planned

### ✅ Working Now
- Full 7-step pipeline from topic → video
- AI topic selection and script generation (Ollama)
- Scene parsing with cinematic prompt enhancement
- Image generation via HuggingFace FLUX
- TTS voice narration via Piper
- Karaoke-style subtitle generation
- Ken Burns motion effects (zoom, pan, rotate)
- Crossfade transitions between scenes
- Subtitle burn-in with styled text
- Docker containerization

### 🔲 Planned / Not Yet Built
- **YouTube auto-upload** (`distribution/youtube_upload.py`) — Use YouTube Data API v3 with OAuth2
- **Instagram auto-upload** (`distribution/instagram_upload.py`) — Use Instagram Graph API or unofficial clients
- **WhisperX-aligned subtitles** (`video/aligned_subtitles.py`) — Code exists but isn't wired into the pipeline; would replace word-count-proportional timing with actual speech alignment
- **Background music** — No music layer currently; could add royalty-free BGM with FFmpeg audio mixing
- **Scheduling / cron** — No scheduler; run manually or set up a cron job / systemd timer
- **Multi-voice / emotion control** — Single voice model; Piper supports multiple voices
- **Error recovery / checkpointing** — Pipeline restarts from scratch on failure; could save progress and resume from last checkpoint
- **Quality verification** — No automated checks on output quality (image relevance, audio clarity, video integrity)

---

## Key Design Decisions

1. **Deterministic scene planner** — `scene_planner.py` uses regex instead of a second LLM call, making it fast and reliable. The script generator's structured prompt ensures consistent `VISUAL: / VOICEOVER:` formatting.

2. **Word-proportional subtitles** — Rather than fixed-time subtitles, timing is distributed by word count, producing more natural reading pace. The 6-word chunk size creates a karaoke-style reveal effect.

3. **Random Ken Burns per scene** — Each scene gets a randomly chosen motion effect, preventing visual monotony across the 5 scenes.

4. **Local-first TTS** — Piper runs entirely offline with a bundled ONNX model, avoiding API costs and latency for voice generation.

5. **Prompt simplification** — Image prompts are truncated to 120 chars before sending to HuggingFace, then re-appended with "cinematic lighting, highly detailed" to optimize generation quality within API limits.
