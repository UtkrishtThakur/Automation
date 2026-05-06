import re


CINEMATIC_SUFFIX = (
    ", cinematic lighting, dramatic atmosphere, ultra detailed, "
    "8k resolution, photorealistic, professional photography"
)


def plan_scenes(script):
    """
    Deterministic scene planner — parses VISUAL/VOICEOVER lines directly
    from the structured script instead of making another LLM call.

    Returns a list of scene dicts:
    [
        {
            "description": "Earth slowly rotating in space",
            "prompt": "Earth slowly rotating in space, cinematic lighting, ...",
            "voiceover": "The universe contains over two trillion galaxies."
        }
    ]
    """

    scenes = []
    current_visual = None
    current_voiceover = None

    for line in script.splitlines():

        stripped = line.strip()

        # Detect SCENE header — flush previous scene
        if re.match(r"^SCENE\s+\d+", stripped, re.IGNORECASE):

            if current_visual is not None:
                scenes.append(_build_scene(current_visual, current_voiceover))

            current_visual = None
            current_voiceover = None

        elif stripped.upper().startswith("VISUAL:"):
            current_visual = stripped.split(":", 1)[1].strip()

        elif stripped.upper().startswith("VOICEOVER:"):
            current_voiceover = stripped.split(":", 1)[1].strip()

    # Flush last scene
    if current_visual is not None:
        scenes.append(_build_scene(current_visual, current_voiceover))

    if not scenes:
        raise ValueError("No scenes could be parsed from script")

    print(f"\nParsed {len(scenes)} scenes from script")

    return scenes


def _build_scene(visual, voiceover):
    """
    Build a scene dict with a cinematic image prompt.
    """

    # Clean the visual description
    description = visual.rstrip(".")

    # Build an optimized prompt for image generation
    prompt = description + CINEMATIC_SUFFIX

    scene = {
        "description": description,
        "prompt": prompt,
    }

    if voiceover:
        scene["voiceover"] = voiceover

    return scene