import os, json
from ..config import settings
def upload(video_path: str, title: str, description: str, tags: list[str]):
    if not settings.YOUTUBE_UPLOAD:
        print("[DRY RUN] Skipping YouTube upload."); return {"id":"dryrun"}
    print(f"[YOUTUBE] (stub) Would upload {video_path} with title='{title}'")
    return {"id":"video123"}
