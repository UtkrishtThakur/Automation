import requests
import time
from pathlib import Path
from app.core.config import config
from app.core.logger import setup_logging
from app.utils.helpers import IMAGES_DIR

log = setup_logging("image_generator")

API_URL = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"


def build_headers():
    token = config.hf_token
    if not token:
        raise RuntimeError("HF_TOKEN not set")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


def optimize_prompt(prompt, max_len=400):
    """
    Redesigns prompt to focus on:
    Subject, Environment, Lighting, Color palette, Camera, Mood, Art style.
    """
    prompt = prompt.replace("VISUAL:", "").strip()
    prompt = re.sub(r"\s+", " ", prompt)
    
    # Consistency keywords are already appended by scene_planner.py via CINEMATIC_SUFFIX
    # Here we just ensure it's not too long and potentially add "low quality" avoidance
    if len(prompt) > max_len:
        prompt = prompt[:max_len-3].rstrip(".") + "..."
        
    return prompt


import re
_optimize_prompt_orig = optimize_prompt


def generate_image(prompt, index, retry=None):
    if retry is None:
        retry = config.max_retry

    optimized = optimize_prompt(prompt)
    output_path = IMAGES_DIR / f"scene_{index}.png"

    log.info(f"Generating image {index}: {optimized[:80]}...")

    for attempt in range(retry):
        try:
            payload = {"inputs": optimized}
            r = requests.post(API_URL, headers=build_headers(), json=payload, timeout=120)

            if r.status_code == 200 and len(r.content) > 50000:
                with open(output_path, "wb") as f:
                    f.write(r.content)
                log.info(f"Saved scene_{index}.png ({len(r.content)//1024}KB)")
                return str(output_path)
            elif r.status_code == 401:
                raise RuntimeError("Invalid HF_TOKEN")
            elif r.status_code == 429:
                wait = int(r.headers.get("Retry-After", 30))
                log.warning(f"Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                log.warning(f"HF attempt {attempt+1}: {r.status_code} {r.text[:200]}")

        except Exception as e:
            log.warning(f"Attempt {attempt+1} error: {e}")

        if attempt < retry - 1:
            time.sleep(config.retry_delay * (attempt + 1))

    raise RuntimeError(f"Image generation failed after {retry} attempts for scene {index}")


def generate_images_batch(scenes):
    results = []
    manifest = {"scenes": [], "generated_at": str(Path(__file__).stat().st_mtime)}

    for i, scene in enumerate(scenes):
        try:
            path = generate_image(scene["prompt"], i)
            results.append(path)
            manifest["scenes"].append({"index": i, "path": path, "prompt": scene["prompt"]})
        except Exception as e:
            log.error(f"Scene {i} FAILED: {e}")
            manifest["scenes"].append({"index": i, "path": None, "error": str(e)})

        if i < len(scenes) - 1:
            time.sleep(2)

    manifest_path = IMAGES_DIR / "manifest.json"
    import json
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    successful = [r for r in results if r]
    log.info(f"Image batch complete: {len(successful)}/{len(scenes)} succeeded")

    return results