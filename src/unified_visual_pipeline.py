"""Unified visual pipeline showing Research feeding into Script generation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field
import uuid

from src.graphs.checkpoints import get_default_checkpointer
from src.models import (
    PipelineDiagnostics,
    ScoredStory,
    ScriptDraft,
    StoryEnriched,
    StoryInput,
    StorySource,
)

# Import nodes from existing graphs
from src.graphs.nodes.fetchers import fetch_story_feeds, load_sheet_metadata
from src.graphs.nodes.enrichers import enrich_stories
from src.graphs.nodes.mergers import merge_and_dedupe
from src.graphs.nodes.rankers import score_stories, select_top_stories
from src.graphs.nodes.script_generation import (
    prepare_story_payload,
    generate_script,
    mark_manual_review,
    finalize_script,
    assess_script,
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


def build_unified_visual_graph() -> StateGraph:
    """Build the unified graph showing Research -> Script flow."""
    
    graph = StateGraph(UnifiedPipelineState)
    
    # Stage 1: Research nodes
    graph.add_node("📊 Load Metadata", load_sheet_metadata)
    graph.add_node("📰 Fetch Feeds", fetch_story_feeds)
    graph.add_node("🔀 Merge Stories", merge_and_dedupe)
    graph.add_node("💎 Enrich Stories", enrich_stories)
    graph.add_node("⭐ Score Stories", score_stories)
    graph.add_node("🎯 Select Top Stories", select_top_stories)
    
    # Bridge node to connect Research to Script
    def bridge_research_to_script(state: UnifiedPipelineState) -> UnifiedPipelineState:
        """Bridge function to pass research output to script generation."""
        print(f"✅ Research complete. Selected {len(state.selected_stories)} stories for script generation.")
        return state
    
    graph.add_node("🔗 Bridge to Script", bridge_research_to_script)
    
    # Stage 2: Script nodes  
    graph.add_node("📝 Prepare Script", prepare_story_payload)
    graph.add_node("✍️ Generate Script", generate_script)
    graph.add_node("👁️ Manual Review", mark_manual_review)
    graph.add_node("✅ Finalize Script", finalize_script)
    
    # Set entry point
    graph.set_entry_point("📊 Load Metadata")
    
    # Stage 1 edges (Research flow)
    graph.add_edge("📊 Load Metadata", "📰 Fetch Feeds")
    graph.add_edge("📰 Fetch Feeds", "🔀 Merge Stories")
    graph.add_edge("🔀 Merge Stories", "💎 Enrich Stories")
    graph.add_edge("💎 Enrich Stories", "⭐ Score Stories")
    graph.add_edge("⭐ Score Stories", "🎯 Select Top Stories")
    
    # Connect Research to Script through bridge
    graph.add_edge("🎯 Select Top Stories", "🔗 Bridge to Script")
    graph.add_edge("🔗 Bridge to Script", "📝 Prepare Script")
    
    # Stage 2 edges (Script flow)
    graph.add_edge("📝 Prepare Script", "✍️ Generate Script")
    graph.add_conditional_edges(
        "✍️ Generate Script",
        assess_script,
        {
            "accept": "✅ Finalize Script",
            "retry": "✍️ Generate Script",
            "manual": "👁️ Manual Review",
        },
    )
    graph.add_edge("👁️ Manual Review", "✅ Finalize Script")
    graph.add_edge("✅ Finalize Script", END)
    
    # Compile with checkpointer
    # Checkpointer removed for LangGraph API
    return graph.compile()


# Entry point for LangGraph
graph = build_unified_visual_graph()
