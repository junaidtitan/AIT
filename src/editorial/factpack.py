def build_factpack(item: dict) -> dict:
    return {
        "headline": item.get("title",""),
        "summary": (item.get("full_text") or "")[:280],
        "sources": [item.get("url")],
        "numbers": [],
        "disclaimers": ["AI-generated draft; verify against sources."]
    }
