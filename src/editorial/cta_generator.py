from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Dict

TEMPLATE_PATH = Path(__file__).resolve().parents[2] / "templates" / "cta_patterns.json"


class CTAGenerator:
    """Generate context-aware CTA questions from pattern library."""

    def __init__(self) -> None:
        with open(TEMPLATE_PATH, "r", encoding="utf-8") as handle:
            self._patterns = json.load(handle)

    def generate(self, topic: str, intent: str | None = None) -> Dict[str, str]:
        choices = self._patterns
        if intent:
            filtered = [p for p in self._patterns if intent in p.get("id", "")]
            if filtered:
                choices = filtered
        pattern = random.choice(choices)
        question = pattern["pattern"].replace("{{topic}}", topic)
        return {"id": pattern["id"], "question": question}


__all__ = ["CTAGenerator"]
