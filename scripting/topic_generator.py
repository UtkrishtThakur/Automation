import requests
import os
import random

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
MODEL = "qwen2.5:7b"


def generate_topics(n=5):

    prompt = f"""
Generate {n} unique educational video topic ideas.

Requirements:
- Each topic must be curiosity-driven and surprising
- Suitable for a 45-90 second narrated educational video
- Should involve real-world science, history, psychology, nature, or technology
- Must be specific enough to explain with facts and data
- Should feel like a Kurzgesagt or Veritasium video title

Return ONLY a numbered list of topic titles, one per line.
No extra text or commentary.
"""

    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={"model": MODEL, "prompt": prompt, "stream": False},
    )

    data = response.json()

    text = data.get("response", "")

    topics = []
    for line in text.split("\n"):
        line = line.strip()
        if line and line[0].isdigit():
            # Strip numbering like "1. " or "1) "
            cleaned = line.lstrip("0123456789.)- ").strip()
            if cleaned:
                topics.append(cleaned)

    return topics if topics else ["Why the universe is expanding faster than we thought"]


def select_topic():
    """
    Fully automated topic selection.
    Generates AI topics and picks one at random.
    """

    topics = generate_topics()

    selected = random.choice(topics)

    print(f"\nAuto-selected topic: {selected}")

    return selected