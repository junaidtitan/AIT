from prefect import flow, task
from uuid import uuid4
import os, json
from datetime import datetime
from src.config import settings
from src.ingest.rss_arxiv import fetch_rss, fetch_fulltext
from src.rank.select import pick_top
from src.approvals.gate import notify, wait
from src.editorial.factpack import build_factpack
from src.editorial.script_daily import generate_script
from src.tts.elevenlabs_tts import synthesize
from src.produce.capcut_stub import assemble
from src.publish.youtube_upload import upload

DATA_DIR = settings.DATA_DIR
os.makedirs(DATA_DIR, exist_ok=True)

@task
def ingest():
    feeds = [s.strip() for s in (settings.RSS_FEEDS or '').split(',') if s.strip()]
    items = fetch_rss(feeds or ["https://openai.com/blog/rss", "http://export.arxiv.org/rss/cs.AI"])
    for it in items[:10]:
        it["full_text"] = fetch_fulltext(it["url"])
    return items

@task
def select_topics(items):
    top = pick_top(items, k=5)
    notify("Topic candidates for today", {"titles":[i["title"] for i in top]})
    wait("topic selection")
    return top

@task
def build_factpacks(items):
    return [build_factpack(i) for i in items]

@task
def draft_script(packs):
    stories = [{"title": p["headline"], "url": p["sources"][0]} for p in packs]
    script = generate_script(stories)
    notify("Draft script ready", {"preview": script.get("vo_script","")[:200]+"…"})
    wait("script approval")
    return script

@task
def voiceover(script):
    wav = os.path.join(DATA_DIR, f"{uuid4()}.wav")
    synthesize(script.get("vo_script",""), wav)
    return [wav]

@task
def render(voice_wavs):
    out_mp4 = os.path.join(DATA_DIR, f"daily_{datetime.now().strftime('%Y%m%d')}.mp4")
    assemble(voice_wavs, assets=[], out_path=out_mp4)
    return out_mp4

@task
def publish(video_path, script):
    title = "Today in AI — Junaid Q"
    desc = "Daily AI news roundup. Sources in video. (AI-assisted production)"
    tags = ["AI","news","machine learning"]
    return upload(video_path, title, desc, tags)

@flow(name="daily_news")
def daily_news():
    items = ingest()
    selected = select_topics(items)
    packs = build_factpacks(selected)
    script = draft_script(packs)
    voice = voiceover(script)
    video = render(voice)
    publish(video, script)

if __name__ == "__main__":
    daily_news()
