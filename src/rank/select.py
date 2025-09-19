"""Ranking helpers for Stage 1 research graph."""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from src.models import ScoredStory, StoryEnriched
from src.utils import canonical_url, content_fingerprint

_DEFAULT_WEIGHTS: Dict[str, float] = {
    "shock": 0.35,
    "future": 0.25,
    "technical": 0.15,
    "recency": 0.15,
    "authority": 0.10,
}


def _score_from_analysis(story: StoryEnriched, weight_overrides: Optional[Dict[str, float]] = None) -> float:
    weights = {**_DEFAULT_WEIGHTS, **(weight_overrides or {})}
    scores = story.analysis.get("scores", {}) if isinstance(story.analysis, dict) else {}
    return sum(weights.get(metric, 0.0) * float(scores.get(metric, 0.0)) for metric in weights)


def _fingerprint(story: StoryEnriched) -> str:
    return story.extras.get("fingerprint") or content_fingerprint(story.url, story.title, story.summary or "")


def score(story: StoryEnriched, weight_overrides: Optional[Dict[str, float]] = None) -> ScoredStory:
    base_score = _score_from_analysis(story, weight_overrides)
    return ScoredStory(
        source=story.source,
        title=story.title,
        url=canonical_url(story.url) or story.url,
        summary=story.summary,
        full_text=story.full_text,
        published_at=story.published_at,
        source_domain=story.source_domain,
        analysis=story.analysis,
        diagnostics=story.diagnostics,
        extras={**story.extras, "fingerprint": _fingerprint(story)},
        score=base_score,
        boosts={},
        companies_mentioned=story.analysis.get("companies", []) if isinstance(story.analysis, dict) else [],
    )


def pick_top(
    stories: Iterable[StoryEnriched],
    k: int = 5,
    *,
    weight_overrides: Optional[Dict[str, float]] = None,
) -> List[ScoredStory]:
    """Rank stories, dedupe by fingerprint, and return the top-k."""
    deduped: Dict[str, ScoredStory] = {}
    for item in stories:
        ranked = score(item, weight_overrides)
        fingerprint = ranked.extras["fingerprint"]
        current = deduped.get(fingerprint)
        if current is None or ranked.score > current.score:
            deduped[fingerprint] = ranked

    ranked_stories = sorted(deduped.values(), key=lambda story: story.score, reverse=True)
    return ranked_stories[:k]


__all__ = ["score", "pick_top"]
