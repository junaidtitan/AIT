import os, time, httpx

CLIENT_ID = os.getenv("PICTORY_CLIENT_ID")
CLIENT_SECRET = os.getenv("PICTORY_CLIENT_SECRET")
BASE = "https://api.pictory.ai/pictory"

def authenticate():
    if not CLIENT_ID or not CLIENT_SECRET:
        raise RuntimeError("PICTORY_CLIENT_ID/SECRET not set")
    
    with httpx.Client(timeout=30) as c:
        r = c.post(f"{BASE}/oauth2/token", data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET
        })
        r.raise_for_status()
        return r.json()["access_token"]

def create_video_from_script(title: str, script: str):
    token = authenticate()
    
    # Create storyboard
    with httpx.Client(timeout=120, headers={"Authorization": f"Bearer {token}"}) as c:
        # Parse script into scenes
        scenes = []
        for paragraph in script.split('\n\n'):
            if paragraph.strip():
                scenes.append({
                    "text": paragraph.strip(),
                    "voiceOver": True,
                    "splitTextOnNewLine": False,
                    "splitTextOnPeriod": True
                })
        
        r = c.post(f"{BASE}/video/storyboard", json={
            "videoName": title,
            "videoDescription": "AI News Briefing",
            "language": "en",
            "scenes": scenes,
            "audio": {
                "aiVoiceOver": {
                    "speaker": "Matthew",
                    "speed": "100",
                    "amplifyLevel": 0
                },
                "autoBackgroundMusic": False
            },
            "output": {"format": "mp4", "resolution": "1080"}
        })
        r.raise_for_status()
        job_id = r.json()["jobId"]
    
    # Wait for storyboard
    time.sleep(10)
    
    # Render video
    with httpx.Client(timeout=120, headers={"Authorization": f"Bearer {token}"}) as c:
        r = c.post(f"{BASE}/video/render", json={"storyboardId": job_id})
        r.raise_for_status()
        render_id = r.json()["renderJobId"]
    
    # Poll for completion
    for _ in range(60):
        time.sleep(10)
        with httpx.Client(timeout=30, headers={"Authorization": f"Bearer {token}"}) as c:
            r = c.get(f"{BASE}/jobs/{render_id}")
            if r.status_code == 200:
                data = r.json()
                if data.get("status") == "completed":
                    return data.get("result", {}).get("videoUrl")
    
    raise TimeoutError("Video render timeout")

def download_video(url: str, out_path: str):
    with httpx.Client(timeout=600) as c:
        r = c.get(url)
        r.raise_for_status()
        with open(out_path, "wb") as f:
            f.write(r.content)
    return out_path

def generate_video(script: str, title: str, out_path: str):
    try:
        video_url = create_video_from_script(title, script)
        if video_url:
            return download_video(video_url, out_path)
    except Exception as e:
        print(f"Pictory error: {e}")
    # Fallback to stub
    with open(out_path, "wb") as f:
        f.write(b"STUB_VIDEO")
    return out_path
