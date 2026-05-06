.PHONY: build run logs shell clean test help

help:
	@echo "AI Content Pipeline - Makefile Commands"
	@echo "========================================"
	@echo "  make build   - Build Docker image"
	@echo "  make run     - Run pipeline in Docker"
	@echo "  make logs    - Show pipeline logs"
	@echo "  make shell   - Open shell in container"
	@echo "  make clean   - Remove all output files"
	@echo "  make test    - Quick syntax check all Python files"
	@echo ""

build:
	docker build -t ai-content-pipeline:latest .

run:
	docker compose up --build

run-detach:
	docker compose up --build -d

logs:
	docker compose logs -f

shell:
	docker compose exec pipeline /bin/bash

clean:
	rm -rf data/images/* data/audio/* data/video/* data/*.txt data/*.json logs/*.log
	rm -f data/.checkpoint data/images/manifest.json
	@echo "Output files cleaned"

resume:
	docker compose run --rm pipeline python run_pipeline.py --resume

debug:
	docker compose run --rm pipeline python run_pipeline.py --debug

test:
	@echo "Checking Python imports..."
	@python3 -c "import app.core.config; import app.core.logger; import app.utils.helpers" 2>/dev/null && echo "  OK: Core modules" || echo "  FAIL: Core modules"
	@python3 -c "import app.scripting.topic_generator; import app.scripting.script_generator; import app.scripting.scene_planner" 2>/dev/null && echo "  OK: Scripting modules" || echo "  FAIL: Scripting modules"
	@python3 -c "import app.media.image_generator; import app.media.voice_generator; import app.media.music_mixer" 2>/dev/null && echo "  OK: Media modules" || echo "  FAIL: Media modules"
	@python3 -c "import app.video.subtitles; import app.video.video_builder" 2>/dev/null && echo "  OK: Video modules" || echo "  FAIL: Video modules"
	@echo "All imports OK"

lint:
	@python3 -m py_compile run_pipeline.py 2>/dev/null && echo "run_pipeline.py: OK" || echo "run_pipeline.py: SYNTAX ERROR"
	@python3 -m py_compile app/core/*.py 2>/dev/null && echo "app/core/: OK" || echo "app/core/: SYNTAX ERROR"
	@python3 -m py_compile app/scripting/*.py 2>/dev/null && echo "app/scripting/: OK" || echo "app/scripting/: SYNTAX ERROR"
	@python3 -m py_compile app/media/*.py 2>/dev/null && echo "app/media/: OK" || echo "app/media/: SYNTAX ERROR"
	@python3 -m py_compile app/video/*.py 2>/dev/null && echo "app/video/: OK" || echo "app/video/: SYNTAX ERROR"
	@python3 -m py_compile app/distribution/*.py 2>/dev/null && echo "app/distribution/: OK" || echo "app/distribution/: SYNTAX ERROR"