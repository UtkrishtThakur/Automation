import requests
import os
import re

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL = "qwen2.5:7b"


def generate_script(topic):

    prompt = f"""
You are a world-class educational video scriptwriter.
Your style is inspired by Kurzgesagt, Veritasium, and VSauce.

Topic:
{topic}

Write a script for a 45-90 second narrated educational video using EXACTLY this format:

SCENE 1
VISUAL: cinematic description of what appears on screen
VOICEOVER: narration text spoken by the narrator

SCENE 2
VISUAL: cinematic description of what appears on screen
VOICEOVER: narration text spoken by the narrator

SCENE 3
VISUAL: cinematic description of what appears on screen
VOICEOVER: narration text spoken by the narrator

SCENE 4
VISUAL: cinematic description of what appears on screen
VOICEOVER: narration text spoken by the narrator

SCENE 5
VISUAL: cinematic description of what appears on screen
VOICEOVER: narration text spoken by the narrator

STRUCTURE:
- SCENE 1 = HOOK: A curiosity-driven opening that grabs attention immediately
- SCENE 2 = EXPLANATION PART 1: Introduce the core concept clearly
- SCENE 3 = EXPLANATION PART 2: Go deeper into the topic
- SCENE 4 = INTERESTING FACT: Include a real statistic, data point, or surprising fact
- SCENE 5 = CURIOSITY ENDING: End with an open question or thought-provoking statement

STRICT RULES:
- Write EXACTLY 5 scenes
- Each VOICEOVER line must be 1-3 sentences of calm, explanatory narration
- Each VISUAL line must describe a single cinematic image
- Include real-world facts, statistics, or scientific data when possible
- Tone must be calm, educational, and engaging
- Do NOT include stage directions, sound effects, or music cues
- Do NOT include anything outside of the SCENE/VISUAL/VOICEOVER format
- Do NOT add introductions, conclusions, or meta-commentary
- VOICEOVER text must flow naturally when read aloud
- Total narration should be 45-90 seconds when spoken
"""

    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
        },
    )

    data = response.json()

    raw_script = data.get("response", "")

    script = clean_script(raw_script)

    if not validate_script(script):
        print("\nWARNING: Script validation failed, using raw output")
        script = raw_script

    return script


def clean_script(script):
    """
    Strip anything outside the expected SCENE/VISUAL/VOICEOVER format.
    Remove markdown artifacts, code fences, extra commentary.
    """

    # Remove markdown code fences
    script = re.sub(r"```[a-z]*\n?", "", script)
    script = script.replace("```", "")

    # Remove markdown formatting
    script = script.replace("**", "")
    script = script.replace("__", "")

    # Keep only lines that are SCENE headers, VISUAL, VOICEOVER, or blank
    cleaned_lines = []
    in_script = False

    for line in script.splitlines():
        stripped = line.strip()

        if re.match(r"^SCENE\s+\d+", stripped, re.IGNORECASE):
            in_script = True
            cleaned_lines.append(stripped.upper() if "scene" in stripped.lower() else stripped)
        elif stripped.upper().startswith("VISUAL:") and in_script:
            cleaned_lines.append(stripped)
        elif stripped.upper().startswith("VOICEOVER:") and in_script:
            cleaned_lines.append(stripped)
        elif stripped == "" and in_script:
            cleaned_lines.append("")

    return "\n".join(cleaned_lines).strip()


def validate_script(script):
    """
    Ensure the script has at least 5 VOICEOVER lines and 5 VISUAL lines.
    """

    voiceover_count = len(re.findall(r"^VOICEOVER:", script, re.MULTILINE | re.IGNORECASE))
    visual_count = len(re.findall(r"^VISUAL:", script, re.MULTILINE | re.IGNORECASE))

    if voiceover_count < 5:
        print(f"Script has only {voiceover_count} VOICEOVER lines (expected >= 5)")
        return False

    if visual_count < 5:
        print(f"Script has only {visual_count} VISUAL lines (expected >= 5)")
        return False

    return True