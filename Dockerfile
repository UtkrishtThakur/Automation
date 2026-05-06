FROM python:3.11-slim

LABEL maintainer="AI Pipeline"
LABEL description="AI Short-Video Content Factory"

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir piper-tts

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=1000:1000 models/ ./models/
COPY --chown=1000:1000 app/ ./app/
COPY --chown=1000:1000 run_pipeline.py .
COPY --chown=1000:1000 config.yaml .

RUN mkdir -p data/images data/audio data/video logs && \
    chown -R 1000:1000 data logs

ENV PYTHONUNBUFFERED=1

CMD ["python", "run_pipeline.py"]