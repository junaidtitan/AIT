"""Ranking nodes for the research LangGraph."""

from __future__ import annotations

from typing import Dict, List

from src.graphs.state import ResearchState
from src.rank.select import score as score_enriched_story


def _apply_trending_boosts(stories: List, trending: Dict[str, float]) -> None:
    if not trending:
        return
    for story in stories:
        text = f"{story.title} {story.summary or ''}".lower()
        for keyword, bonus in trending.items():
            if keyword.lower() in text:
                story.score += bonus
                story.boosts.setdefault(f"trend:{keyword}", bonus)


def score_stories(state: ResearchState) -> ResearchState:
    if not state.enriched_stories:
        return state
    weight_overrides = state.metadata.get("rank_weights") if isinstance(state.metadata, dict) else None
    scored = [score_enriched_story(story, weight_overrides) for story in state.enriched_stories]
    _apply_trending_boosts(scored, state.trending_keywords)
    scored.sort(key=lambda item: item.score, reverse=True)
    state.scored_stories = scored
    state.diagnostics.record("info", "scored_stories", count=len(scored))
    return state


def select_top_stories(state: ResearchState) -> ResearchState:
    if not state.scored_stories:
        return state
    limit = state.metadata.get("selection_limit", 6) if isinstance(state.metadata, dict) else 6
    state.selected_stories = state.scored_stories[:limit]
    for idx, story in enumerate(state.selected_stories, start=1):
        story.rank = idx
    state.diagnostics.record("info", "selected_stories", count=len(state.selected_stories))
    return state
