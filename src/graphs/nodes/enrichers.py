"""Enrichment nodes for the research LangGraph."""

from __future__ import annotations

from src.editorial.story_analyzer import StoryAnalyzer
from src.graphs.state import ResearchState
from src.models import StoryEnriched


def enrich_stories(state: ResearchState) -> ResearchState:
    if not state.raw_stories:
        return state
    analyzer = StoryAnalyzer()
    payload = [story.model_dump() for story in state.raw_stories]
    analyzed = analyzer.analyze(payload)
    state.enriched_stories = [StoryEnriched.model_validate(item) for item in analyzed]
    state.diagnostics.record("info", "enriched_stories", count=len(state.enriched_stories))
    return state
