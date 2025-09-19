"""Story data models shared by LangGraph ingestion and ranking."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, model_validator


def _extract_domain(url: str | None) -> str | None:
    if not url:
        return None
    try:
        parsed = urlparse(url)
        return parsed.netloc or None
    except ValueError:
        return None


class StorySource(BaseModel):
    """Configuration for a news or research feed."""

    name: str
    url: str
    category: str = "news"
    priority: int = 5
    weight: float = 1.0
    enabled: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StoryInput(BaseModel):
    """Raw story as fetched from a source before enrichment."""

    source: StorySource
    title: str
    url: str
    summary: Optional[str] = None
    full_text: Optional[str] = None
    published_at: Optional[datetime] = None
    source_domain: Optional[str] = None
    language: Optional[str] = None
    extras: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _ensure_domain(self) -> "StoryInput":
        if not self.source_domain:
            self.source_domain = _extract_domain(self.url)
        return self

    @property
    def canonical_id(self) -> str:
        return self.extras.get("canonical_id") or self.url


class StoryEnriched(StoryInput):
    """Story after enrichment, analysis, and dedupe."""

    analysis: Dict[str, Any] = Field(default_factory=dict)
    diagnostics: Dict[str, Any] = Field(default_factory=dict)


class ScoredStory(StoryEnriched):
    """Story with ranking metadata produced by Stage 1."""

    score: float = 0.0
    rank: Optional[int] = None
    boosts: Dict[str, float] = Field(default_factory=dict)
    companies_mentioned: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _round_score(self) -> "ScoredStory":
        self.score = float(round(self.score, 6))
        return self


__all__ = [
    "StorySource",
    "StoryInput",
    "StoryEnriched",
    "ScoredStory",
]
