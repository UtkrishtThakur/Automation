import requests
import os
import time

OUTPUT_DIR = "data/images"
os.makedirs(OUTPUT_DIR, exist_ok=True)

HF_TOKEN = os.getenv("HF_TOKEN")

API_URL = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"

headers = {
    "Authorization": f"Bearer {HF_TOKEN}",
    "Content-Type": "application/json"
}


def simplify_prompt(prompt):
    prompt = prompt.split(".")[0]
    return prompt[:120]


def generate_image(prompt, index):

    prompt = simplify_prompt(prompt)
    prompt = f"{prompt}, cinematic lighting, highly detailed"

    payload = {"inputs": prompt}

    print(f"Generating image {index} → {prompt}")

    for attempt in range(5):

        r = requests.post(API_URL, headers=headers, json=payload)

        if r.status_code == 200:

            path = f"{OUTPUT_DIR}/scene_{index}.png"

            with open(path, "wb") as f:
                f.write(r.content)

            print("Saved →", path)
            return path

        else:
            print("HF error:", r.status_code, r.text)
            time.sleep(3)

    raise Exception("Image generation failed")