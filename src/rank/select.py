from datetime import datetime, timezone
def _recency_score(iso_ts):
    if not iso_ts: return 0.0
    try:
        dt = datetime.fromisoformat(iso_ts.replace('Z','+00:00'))
        age = (datetime.now(timezone.utc) - dt.replace(tzinfo=timezone.utc)).total_seconds()
        return max(0.0, 1.0 - age/(3*24*3600))
    except: return 0.5

AUTH = {"openai.com":1.0,"deepmind.google":0.95,"arxiv.org":0.9}
def score(item: dict) -> float:
    recency = _recency_score(item.get("published_ts"))
    authority = AUTH.get(item.get("source_domain",""), 0.5)
    novelty = 0.5
    return 0.45*recency + 0.35*authority + 0.20*novelty

def pick_top(items: list[dict], k=5) -> list[dict]:
    return sorted(items, key=score, reverse=True)[:k]
