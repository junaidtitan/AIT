"""Unified visual pipeline configured via Langflow."""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from langgraph.graph import StateGraph
from pydantic import BaseModel, Field


from src.models import (
    PipelineDiagnostics,
    ScoredStory,
    ScriptDraft,
    StoryEnriched,
    StoryInput,
    StorySource,
)


class UnifiedPipelineState(BaseModel):
    """Combined state for Research -> Script pipeline."""

    # Common
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # Stage 1 – Research
    sources: List[StorySource] = Field(default_factory=list)
    raw_stories: List[StoryInput] = Field(default_factory=list)
    enriched_stories: List[StoryEnriched] = Field(default_factory=list)
    scored_stories: List[ScoredStory] = Field(default_factory=list)
    selected_stories: List[ScoredStory] = Field(default_factory=list)
    companies: Dict[str, List[str]] = Field(default_factory=dict)
    scoring_weights: Dict[str, float] = Field(default_factory=dict)
    trending_keywords: Dict[str, float] = Field(default_factory=dict)
    hours_filter: Optional[int] = None

    # Stage 2 – Script
    analysis: Dict[str, Any] = Field(default_factory=dict)
    segments: List[Dict[str, Any]] = Field(default_factory=list)
    draft: Optional[ScriptDraft] = None
    validation: Optional[Dict[str, Any]] = None
    final_script: Optional[ScriptDraft] = None
    attempts: int = 0
    manual_review: bool = False

    # Shared metadata / diagnostics
    errors: List[str] = Field(default_factory=list)
    diagnostics: PipelineDiagnostics = Field(default_factory=PipelineDiagnostics)
    checkpoints: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


CONFIG_PATH = Path(__file__).resolve().parents[1] / "langflow" / "pipeline_config.json"


def build_unified_visual_graph() -> StateGraph:
    """Build the unified graph based on the Langflow-authored config."""

    from langflow_support import build_graph_from_file

    return build_graph_from_file(CONFIG_PATH)


# Entry point for LangGraph
graph = build_unified_visual_graph()
