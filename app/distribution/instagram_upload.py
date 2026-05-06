import httpx
import os
from pathlib import Path
from app.core.config import config
from app.core.logger import setup_logging

log = setup_logging("instagram_upload")

GRAPH_API = "https://graph.instagram.com"
ME_API = "https://graph.instagram.com/me"


def check_token():
    token = config.instagram_access_token
    if not token:
        raise RuntimeError(
            "Instagram upload requires INSTAGRAM_ACCESS_TOKEN. "
            "Get from Meta Developer Console: https://developers.facebook.com"
        )

    response = httpx.get(
        ME_API,
        params={
            "fields": "id,username,account_type,media_count",
            "access_token": token
        },
        timeout=30
    )

    if response.status_code != 200:
        raise RuntimeError(f"Invalid Instagram token: {response.text}")

    data = response.json()
    log.info(f"Instagram account: @{data.get('username')} ({data.get('account_type')})")
    return data


def get_long_lived_token():
    token = config.instagram_access_token
    response = httpx.get(
        "https://graph.facebook.com/v18.0/oauth/access_token",
        params={
            "grant_type": "fb_exchange_token",
            "client_id": os.getenv("FB_CLIENT_ID", ""),
            "client_secret": os.getenv("FB_CLIENT_SECRET", ""),
            "fb_exchange_token": token
        },
        timeout=30
    )

    if response.status_code == 200:
        return response.json().get("access_token")
    return token


def upload_reel(video_path, caption=""):
    log.info(f"Starting Instagram upload: {video_path}")

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")

    token = get_long_lived_token()

    account = check_token()

    container_response = httpx.post(
        f"{GRAPH_API}/me/media",
        params={"access_token": token},
        json={
            "media_type": "REELS",
            "video_url": f"file://{os.path.abspath(video_path)}",
            "caption": caption[:2200],
            "share_to_feed": True
        },
        timeout=120
    )

    if container_response.status_code != 200:
        raise RuntimeError(f"Instagram container creation failed: {container_response.text}")

    creation_id = container_response.json().get("id")

    publish_response = httpx.post(
        f"{GRAPH_API}/me/media_publish",
        params={"access_token": token},
        json={"creation_id": creation_id},
        timeout=60
    )

    if publish_response.status_code != 200:
        raise RuntimeError(f"Instagram publish failed: {publish_response.text}")

    media_id = publish_response.json().get("id")
    log.info(f"Instagram Reel uploaded: media_id={media_id}")
    return media_id


def generate_caption(topic, script):
    caption = f"""🎬 {topic}

{script[:150]}...

#reels #education #science #documentary #shorts #aitube #learning"""

    return caption.strip()[:2200]