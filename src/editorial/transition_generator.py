from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Iterable, List, Optional

TEMPLATE_PATH = Path(__file__).resolve().parents[2] / "templates" / "transition_phrases.json"


class TransitionGenerator:
    """Serve energetic transition phrases from the library."""

    def __init__(self) -> None:
        with open(TEMPLATE_PATH, "r", encoding="utf-8") as handle:
            self._phrases = json.load(handle)

    def pick(self, tag_candidates: List[str], used: Optional[Iterable[str]] = None) -> str:
        used_set = set(used or [])
        candidate_set = {tag for tag in tag_candidates if tag}

        def entry_tags(entry: dict) -> List[str]:
            tags = entry.get("tags")
            if isinstance(tags, list):
                return [str(tag) for tag in tags if tag]
            tag = entry.get("tag")
            return [str(tag)] if tag else []

        available: List[str] = []
        for entry in self._phrases:
            tags = entry_tags(entry)
            if not tags:
                continue
            if candidate_set & set(tags):
                available.append(entry["phrase"])

        if not available:
            available = [p["phrase"] for p in self._phrases]

        remaining = [phrase for phrase in available if phrase not in used_set]
        choices = remaining or available
        return random.choice(choices)


__all__ = ["TransitionGenerator"]
