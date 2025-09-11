import feedparser, requests, datetime as dt
from bs4 import BeautifulSoup
from readability import Document
from urllib.parse import urlparse

def domain_of(u: str) -> str:
    try: return urlparse(u).netloc
    except: return ""

def fetch_rss(feeds: list[str]) -> list[dict]:
    items = []
    for url in feeds:
        d = feedparser.parse(url)
        for e in d.entries[:20]:
            link = getattr(e,'link',None)
            if not link: continue
            title = getattr(e,'title','')
            published = getattr(e,'published_parsed', None)
            ts = dt.datetime(*published[:6]) if published else None
            items.append({
                "url": link,
                "source_domain": domain_of(link),
                "published_ts": ts.isoformat() if ts else None,
                "title": title,
                "full_text": None
            })
    return items

def fetch_fulltext(url: str) -> str | None:
    try:
        html = requests.get(url, timeout=10).text
        doc = Document(html).summary()
        soup = BeautifulSoup(doc, 'html5lib')
        return soup.get_text(" ", strip=True)
    except Exception:
        return None
