from __future__ import annotations

import os
import re
from typing import Dict

import httpx

from ..config import settings

_WEAK_VERBS = {
    "is": "drives",
    "are": "fuel",
    "was": "triggered",
    "were": "sparked",
    "be": "become",
    "has": "delivers",
    "have": "deliver",
    "will": "is set to",
    "shows": "signals",
    "show": "signal",
    "make": "force",
    "made": "forced",
}
_PASSIVE_PATTERN = re.compile(r"\b(is|are|was|were|be|been)\s+(?:being\s+)?(\w+ed)\b", re.IGNORECASE)


class ToneEnhancer:
    """Apply rule-based tone adjustments with optional LLM polish."""

    def __init__(self, enable_llm: bool = False) -> None:
        self.enable_llm = enable_llm and bool(settings.OPENAI_API_KEY)

    def enhance(self, text: str) -> Dict[str, str]:
        adjusted = self._apply_rules(text)
        final_text = adjusted
        llm_used = False
        if self.enable_llm:
            llm_output = self._llm_pass(adjusted)
            if llm_output:
                final_text = llm_output
                llm_used = True
        return {"text": final_text, "llm_used": llm_used}

    def _apply_rules(self, text: str) -> str:
        def replace_passive(match: re.Match[str]) -> str:
            verb = match.group(2)
            return f"{verb.capitalize()}"

        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        rewrites = []
        for sentence in sentences:
            revised = _PASSIVE_PATTERN.sub(replace_passive, sentence)
            words = revised.split()
            if words:
                first = words[0].lower()
                if first in {"there", "here"} and len(words) > 1:
                    revised = " ".join(words[1:])
            for weak, strong in _WEAK_VERBS.items():
                revised = re.sub(rf"\b{weak}\b", strong, revised)
            rewrites.append(revised)
        return " ".join(rewrites)

    def _llm_pass(self, text: str) -> str:
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": "Rewrite the briefing in active voice with strong, urgent verbs. Keep factual content intact."
                },
                {"role": "user", "content": text}
            ],
            "temperature": 0.3
        }
        try:
            with httpx.Client(timeout=30) as client:
                response = client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                    json=payload,
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"].strip()
        except Exception:
            return text


__all__ = ["ToneEnhancer"]
