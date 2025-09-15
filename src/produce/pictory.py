import os, time, httpx

API_KEY = os.getenv("PICTORY_API_KEY")
BASE = os.getenv("PICTORY_API_BASE", "https://api.pictory.ai")

def _client():
    if not API_KEY:
        raise RuntimeError("PICTORY_API_KEY not set")
    return httpx.Client(timeout=120, headers={"Authorization": f"Bearer {API_KEY}"})

def create_project_from_script(title: str, script: str):
    with _client() as c:
        r = c.post(f"{BASE}/v1/projects", json={
            "title": title,
            "workflow": "text-to-video",
            "inputs": {"script": script},
            "brand": {"applyBrandKit": True}
        })
        r.raise_for_status()
        return r.json()["projectId"]

def request_render(project_id: str, aspect="16:9", voiceover=False):
    with _client() as c:
        r = c.post(f"{BASE}/v1/projects/{project_id}/render", json={
            "aspectRatio": aspect,
            "useVoiceover": voiceover,
            "captions": True
        })
        r.raise_for_status()
        return r.json()["renderId"]

def wait_for_render(render_id: str, poll=10, timeout=1800):
    with _client() as c:
        t0 = time.time()
        while True:
            r = c.get(f"{BASE}/v1/renders/{render_id}")
            r.raise_for_status()
            data = r.json()
            if data["status"] in ("succeeded","failed"):
                return data
            if time.time() - t0 > timeout:
                raise TimeoutError("Pictory render timeout")
            time.sleep(poll)

def download_result(render_info: dict, out_path: str):
    url = render_info["output"]["url"]
    with httpx.Client(timeout=600) as c:
        with c.stream("GET", url) as resp:
            resp.raise_for_status()
            with open(out_path, "wb") as f:
                for chunk in resp.iter_bytes():
                    f.write(chunk)
    return out_path
