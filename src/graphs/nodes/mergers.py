"""Merge and dedupe nodes for the research LangGraph."""

from __future__ import annotations

from typing import Dict

from src.graphs.state import ResearchState
from src.utils import content_fingerprint


def merge_and_dedupe(state: ResearchState) -> ResearchState:
    seen: Dict[str, int] = {}
    unique = []
    for story in state.raw_stories:
        fingerprint = story.extras.get("fingerprint") or content_fingerprint(story.url, story.title)
        if fingerprint in seen:
            continue
        story.extras["fingerprint"] = fingerprint
        seen[fingerprint] = 1
        unique.append(story)
    state.raw_stories = unique
    state.diagnostics.record("info", "dedupe_complete", count=len(unique))
    return state
