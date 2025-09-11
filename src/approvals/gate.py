import time, json, os, requests
from ..config import settings

def notify(text: str, payload: dict | None = None):
    if settings.SLACK_BOT_TOKEN and settings.SLACK_CHANNEL_ID:
        url = "https://slack.com/api/chat.postMessage"
        headers = {"Authorization": f"Bearer {settings.SLACK_BOT_TOKEN}"}
        blocks = [{
            "type":"section","text":{"type":"mrkdwn","text":text}
        }]
        if payload:
            blocks.append({"type":"section","text":{"type":"mrkdwn","text":"```"+json.dumps(payload,indent=2)[:2800]+"```"}})
        blocks.append({"type":"actions","elements":[
            {"type":"button","text":{"type":"plain_text","text":"Approve"},"style":"primary","value":"approve"},
            {"type":"button","text":{"type":"plain_text","text":"Revise"},"style":"danger","value":"revise"}
        ]})
        requests.post(url, headers=headers, json={"channel": settings.SLACK_CHANNEL_ID, "text": text, "blocks": blocks})
    else:
        print("[APPROVAL NOTICE]", text)
        if payload: print(json.dumps(payload, indent=2))

def wait(what: str):
    if settings.APPROVAL_MODE == "auto":
        print(f"[AUTO MODE] {what} auto-approved.")
        return "auto"
    try:
        return input(f"Awaiting manual approval for {what} — type 'approve' to continue: ").strip().lower()
    except EOFError:
        time.sleep(5); return "approve"
