import requests
import re
from app.core.config import config
from app.core.logger import setup_logging

log = setup_logging("script_generator")

SCRIPT_TEMPLATE = """You are a world-class educational video scriptwriter.
Your style is inspired by Kurzgesagt, Veritasium, and VSauce.

Topic: {topic}

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

SCENE STRUCTURE:
- SCENE 1 = HOOK: A curiosity-driven opening that grabs attention immediately with a surprising fact or question
- SCENE 2 = EXPLANATION PART 1: Introduce the core concept clearly with visual analogy
- SCENE 3 = EXPLANATION PART 2: Go deeper with real data or mechanism
- SCENE 4 = WOW FACT: Include a real statistic, data point, or jaw-dropping fact with numbers
- SCENE 5 = CURIOSITY ENDING: End with an open question or thought-provoking statement

STRICT RULES:
- Write EXACTLY 5 scenes
- Each VOICEOVER must be 15-30 words for optimal TTS pacing (45-90 seconds total)
- Each VISUAL must describe a single cinematic, visually striking image
- Include specific real-world facts, statistics, or scientific data
- Tone: calm, educational, authoritative yet curious
- NO stage directions, sound effects, music cues, or meta-commentary
- NO introductions or conclusions outside the 5-scene format
- VOICEOVER text must flow naturally when read aloud
- Do NOT use markdown formatting, asterisks, or special characters"""


def call_ollama(prompt, max_tokens=512):
    for attempt in range(config.max_retry):
        try:
            response = requests.post(
                f"{config.ollama_url}/api/generate",
                json={
                    "model": config.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": max_tokens,
                        "stop": ["```", "NOTES:", "---"]
                    }
                },
                timeout=120
            )
            response.raise_for_status()
            return response.json().get("response", "")
        except Exception as e:
            log.warning(f"Ollama attempt {attempt+1}: {e}")

    raise RuntimeError(f"Script generation failed after {config.max_retry} attempts")


def clean_script(script):
    script = re.sub(r"```[a-z]*\n?", "", script)
    script = script.replace("```", "")
    script = re.sub(r"\|\s*[^|]+\s*\|", "", script)

    lines = []
    in_script = False
    for line in script.splitlines():
        stripped = line.strip()
        if re.match(r"^SCENE\s+\d+", stripped, re.IGNORECASE):
            in_script = True
            lines.append(re.sub(r"^SCENE\s+", "SCENE ", stripped).upper())
        elif stripped.upper().startswith("VISUAL:") and in_script:
            lines.append(stripped.replace("VISUAL:", "VISUAL:", 1))
        elif stripped.upper().startswith("VOICEOVER:") and in_script:
            lines.append(stripped.replace("VOICEOVER:", "VOICEOVER:", 1))
        elif stripped == "" and in_script:
            lines.append("")

    result = "\n".join(lines).strip()
    if not result:
        raise ValueError("Script cleaned to empty string")
    return result


def validate_script(script):
    voiceover_count = len(re.findall(r"^VOICEOVER:", script, re.MULTILINE | re.IGNORECASE))
    visual_count = len(re.findall(r"^VISUAL:", script, re.MULTILINE | re.IGNORECASE))

    log.info(f"Script validation: {voiceover_count} VOICEOVER lines, {visual_count} VISUAL lines")

    if voiceover_count < 5 or visual_count < 5:
        log.error(f"Script validation FAILED: {voiceover_count}V/{visual_count}W (need 5+ each)")
        return False
    return True


def generate_script(topic, topic_override=None):
    log.info(f"Generating script for topic: {topic}")

    prompt = SCRIPT_TEMPLATE.format(topic=topic)

    raw = call_ollama(prompt, max_tokens=1024)
    script = clean_script(raw)

    if not validate_script(script):
        log.warning("Primary script validation failed, attempting regeneration...")
        raw2 = call_ollama(prompt + "\n\nIMPORTANT: Return ONLY the 5-scene script in the exact format shown. No commentary.", max_tokens=1024)
        script = clean_script(raw2)
        if not validate_script(script):
            raise RuntimeError("Script generation validation failed twice")

    word_count = sum(len(re.findall(r"\w+", vo.split(":", 1)[1]))
                     for vo in re.findall(r"^VOICEOVER:.*", script, re.MULTILINE))
    est_duration = word_count / 2.5
    log.info(f"Script generated: ~{est_duration:.0f}s ({word_count} words, {len(script)} chars)")

    return script