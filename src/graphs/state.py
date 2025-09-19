"""Shared LangGraph state models."""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.models import PipelineDiagnostics, ScoredStory, ScriptDraft, StoryEnriched, StoryInput, StorySource


class ResearchState(BaseModel):
    """State container passed through the research graph."""

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sources: List[StorySource] = Field(default_factory=list)
    raw_stories: List[StoryInput] = Field(default_factory=list)
    enriched_stories: List[StoryEnriched] = Field(default_factory=list)
    scored_stories: List[ScoredStory] = Field(default_factory=list)
    selected_stories: List[ScoredStory] = Field(default_factory=list)
    companies: Dict[str, List[str]] = Field(default_factory=dict)
    scoring_weights: Dict[str, float] = Field(default_factory=dict)
    trending_keywords: Dict[str, float] = Field(default_factory=dict)
    hours_filter: Optional[int] = None
    diagnostics: PipelineDiagnostics = Field(default_factory=PipelineDiagnostics)
    errors: List[str] = Field(default_factory=list)
    checkpoints: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ScriptState(BaseModel):
    """State container for the script generation graph."""

    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    selected_stories: List[ScoredStory] = Field(default_factory=list)
    analysis: Dict[str, Any] = Field(default_factory=dict)
    segments: List[Dict[str, Any]] = Field(default_factory=list)
    draft: Optional[ScriptDraft] = None
    validation: Optional[Dict[str, Any]] = None
    final_script: Optional[ScriptDraft] = None
    attempts: int = 0
    errors: List[str] = Field(default_factory=list)
    diagnostics: PipelineDiagnostics = Field(default_factory=PipelineDiagnostics)
    checkpoints: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    manual_review: bool = False


__all__ = ["ResearchState", "ScriptState"]
