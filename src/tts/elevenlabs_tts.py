import os, httpx
from pydub import AudioSegment
from ..config import settings

def synthesize(text: str, out_path: str) -> str:
    if not (settings.ELEVENLABS_API_KEY and settings.ELEVENLABS_VOICE_ID):
        AudioSegment.silent(duration=1000).export(out_path, format="wav")
        return out_path
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{settings.ELEVENLABS_VOICE_ID}"
    headers = {"xi-api-key": settings.ELEVENLABS_API_KEY, "accept": "audio/mpeg"}
    payload = {"text": text, "voice_settings": {"stability": 0.4, "similarity_boost": 0.6}}
    with httpx.Client(timeout=60) as c:
        r = c.post(url, headers=headers, json=payload)
        r.raise_for_status()
        tmp = out_path.replace(".wav",".mp3")
        with open(tmp,"wb") as f: f.write(r.content)
    AudioSegment.from_mp3(tmp).export(out_path, format="wav")
    return out_path
