from __future__ import annotations

import json
import random
from pathlib import Path
from typing import List

TEMPLATE_PATH = Path(__file__).resolve().parents[2] / "templates" / "transition_phrases.json"


class TransitionGenerator:
    """Serve energetic transition phrases from the library."""

    def __init__(self) -> None:
        with open(TEMPLATE_PATH, "r", encoding="utf-8") as handle:
            self._phrases = json.load(handle)

    def pick(self, tag_candidates: List[str]) -> str:
        available = [p["phrase"] for p in self._phrases if p.get("tag") in tag_candidates]
        if not available:
            available = [p["phrase"] for p in self._phrases]
        return random.choice(available)


__all__ = ["TransitionGenerator"]
