import requests
import random
from app.core.config import config
from app.core.logger import setup_logging

log = setup_logging("topic_generator")

def generate_topics(n=5):
    prompt = f"""Generate {n} unique educational video topic ideas.

Requirements:
- Each topic must be curiosity-driven and surprising
- Suitable for a 45-90 second narrated educational video
- Should involve real-world science, history, psychology, nature, or technology
- Must be specific enough to explain with facts and data
- Should feel like a Kurzgesagt or Veritasium video title

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