import re
from app.core.logger import setup_logging

log = setup_logging("scene_planner")

CINEMATIC_SUFFIX = (
    ", cinematic lighting, dramatic atmosphere, ultra detailed, "
    "8k resolution, photorealistic, professional cinematography, "
    "award-winning documentary style"
)


def plan_scenes(script):
    scenes = []
    current_visual = None
    current_voiceover = None

    for line in script.splitlines():
        stripped = line.strip()

        if re.match(r"^SCENE\s+\d+", stripped, re.IGNORECASE):
            if current_visual is not None:
                scenes.append(_build_scene(current_visual, current_voiceover))
            current_visual = None
            current_voiceover = None

        elif stripped.upper().startswith("VISUAL:"):
            current_visual = stripped.split(":", 1)[1].strip()

        elif stripped.upper().startswith("VOICEOVER:"):
            current_voiceover = stripped.split(":", 1)[1].strip()

    if current_visual is not None:
        scenes.append(_build_scene(current_visual, current_voiceover))

    if not scenes:
        raise ValueError("No scenes could be parsed from script")

    log.info(f"Parsed {len(scenes)} scenes from script")
    return scenes


def _build_scene(visual, voiceover):
    description = visual.rstrip(".")

    if len(description) > 150:
        description = description[:147] + "..."

    prompt = description + CINEMATIC_SUFFIX

    return {
        "description": description,
        "prompt": prompt,
        "voiceover": voiceover or ""
    }