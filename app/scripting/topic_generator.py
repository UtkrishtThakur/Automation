import requests
import random
from app.core.config import config
from app.core.logger import setup_logging

log = setup_logging("topic_generator")

def generate_topics(n=5):
    prompt = f"""Generate {n} unique, highly visual educational video topic ideas.

Requirements:
- Each topic must be curiosity-driven, mind-bending, or surprising.
- Examples: "Why black holes are invisible", "What if Earth stopped spinning?", "How GPS proves Einstein right".
- Topics must be SPECIFIC and visually suggest cinematic science illustrations.
- Style: Veritasium, Kurzgesagt, or TED-Ed.
- Avoid boring, dry, or textbook subjects.

Return ONLY a numbered list of topic titles, one per line.
No extra text or commentary."""

    for attempt in range(config.max_retry):
        try:
            response = requests.post(
                f"{config.ollama_url}/api/generate",
                json={
                    "model": config.ollama_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.9, "num_predict": 256}
                },
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            text = data.get("response", "")

            topics = []
            for line in text.split("\n"):
                line = line.strip()
                if line and line[0].isdigit():
                    cleaned = line.lstrip("0123456789.)- ").strip()
                    if cleaned and len(cleaned) > 5:
                        topics.append(cleaned)

            if topics:
                log.info(f"Generated {len(topics)} topics")
                return topics

        except Exception as e:
            log.warning(f"Ollama attempt {attempt+1} failed: {e}")

    log.warning("Using fallback topics")
    return [
        "Why the universe is expanding faster than we thought",
        "The bacteria living inside your body",
        "How black holes shape galaxies",
        "The surprising math behind nature's patterns",
        "What happens when continents collide"
    ]


def select_topic(topic_override=None):
    if topic_override:
        log.info(f"Using provided topic: {topic_override}")
        return topic_override

    topics = generate_topics()
    selected = random.choice(topics)
    log.info(f"Selected topic: {selected}")
    return selected