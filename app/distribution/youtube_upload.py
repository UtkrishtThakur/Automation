import os
import httpx
import json
from pathlib import Path
from app.core.config import config
from app.core.logger import setup_logging

log = setup_logging("youtube_upload")

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly"
]

CREDENTIALS_FILE = Path("data/.youtube_credentials.json")
TOKEN_FILE = Path("data/.youtube_token.json")


def get_credentials():
    import google_auth_oauthlib.flow
    client_id = config.youtube_client_id
    client_secret = config.youtube_client_secret

    if not client_id or not client_secret:
        raise RuntimeError(
            "YouTube upload requires YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET. "
            "Get these from https://console.cloud.google.com/apis/credentials"
        )

    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uris": ["http://localhost"]
            }
        },
        SCOPES
    )
    credentials = flow.run_local_server(port=0, prompt="consent")
    return credentials


def get_access_token(credentials):
    return credentials.token


def upload_video(video_path, title, description, tags=None, category_id="28"):
    log.info(f"Starting YouTube upload: {video_path}")

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video not found: {video_path}")

    credentials = None
    if TOKEN_FILE.exists():
        import google_auth_oauthlib.flow
        try:
            credentials = google_auth_oauthlib.flow.InstalledAppFlow.from_authorized_user_file(
                str(TOKEN_FILE), SCOPES
            )
        except:
            credentials = None

    if not credentials:
        log.info("No cached credentials, launching OAuth flow...")
        credentials = get_credentials()
        with open(TOKEN_FILE, "w") as f:
            f.write(credentials.to_json())

    access_token = get_access_token(credentials)

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    video_snippet = {
        "title": title[:100],
        "description": description[:5000],
        "tags": (tags or [])[:500],
        "categoryId": category_id,
        "defaultLanguage": "en"
    }

    status = {
        "privacyStatus": "public",
        "selfDeclaredMadeForKids": False
    }

    request_body = {
        "snippet": video_snippet,
        "status": status
    }

    import io
    video_size = os.path.getsize(video_path)

    upload_url = "https://upload.youtube.com/v3/uploads"
    init_url = "https://www.googleapis.com/upload/youtube/v3/videos"

    init_response = httpx.post(
        init_url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Upload-Content-Length": str(video_size),
            "X-Upload-Content-Type": "video/mp4"
        },
        json={
            "snippet": video_snippet,
            "status": status
        },
        timeout=60
    )

    if init_response.status_code not in (200, 201):
        log.error(f"YouTube init failed: {init_response.status_code} {init_response.text}")
        raise RuntimeError(f"YouTube upload init failed: {init_response.text}")

    video_id = init_response.json().get("id")
    upload_url_final = f"{init_url}/{video_id}"

    with open(video_path, "rb") as f:
        video_data = f.read()

    upload_response = httpx.post(
        f"{upload_url_final}?uploadType=resumable",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "video/mp4",
            "Content-Length": str(video_size),
            "X-Upload-Content-Type": "video/mp4"
        },
        content=video_data,
        timeout=300
    )

    if upload_response.status_code in (200, 201):
        log.info(f"YouTube upload complete: https://youtube.com/watch?v={video_id}")
        return f"https://youtube.com/watch?v={video_id}"
    else:
        log.error(f"YouTube upload failed: {upload_response.status_code} {upload_response.text}")
        raise RuntimeError(f"YouTube upload failed: {upload_response.text}")


def generate_description(topic, script, scenes):
    description = f"""Educational video about: {topic}

Created with AI • {script[:200]}

🔔 Subscribe for more educational content!

#education #science #documentary #aitube #shorts
"""
    return description.strip()


def generate_tags(topic):
    base_tags = ["education", "science", "documentary", "shorts", "aitube", "facts"]
    topic_words = [w for w in topic.split() if len(w) > 3]
    return base_tags + topic_words[:15]