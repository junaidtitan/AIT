import json, os, httpx
from ..config import settings

def generate_script(stories: list[dict]) -> dict:
    tmpl = open("templates/prompt_script_daily.txt","r").read()
    prompt = tmpl.replace("{{stories_json}}", json.dumps(stories, ensure_ascii=False))
    api = settings.OPENAI_API_KEY
    if not api:
        text = "[HOOK] Today in AI: key moves.\n" + "\n".join(f"[STORY] {s.get('title')}" for s in stories)
        return {"vo_script": text, "lower_thirds":[s.get("title","Story") for s in stories], "broll_keywords":["ai"], "chapters":[]}
    with httpx.Client(timeout=60) as c:
        r = c.post("https://api.openai.com/v1/chat/completions",
                   headers={"Authorization": f"Bearer {api}"},
                   json={"model":"gpt-4o","messages":[{"role":"user","content":prompt}]})
        r.raise_for_status()
        txt = r.json()["choices"][0]["message"]["content"]
    return {"vo_script": txt, "lower_thirds":[s.get("title","Story") for s in stories], "broll_keywords":["ai"], "chapters":[]}
