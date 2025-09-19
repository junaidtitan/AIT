"""Unified visual pipeline showing all stages connected."""

from langgraph.graph import END, StateGraph
from typing import TypedDict, List, Dict, Any, Optional

# Import all node functions from both graphs
from src.graphs.nodes.metadata import load_metadata
from src.graphs.nodes.feed_fetcher import fetch_feeds
from src.graphs.nodes.merge import merge_sources
from src.graphs.nodes.enrichment import enrich_stories
from src.graphs.nodes.scoring import score_stories
from src.graphs.nodes.selection import select_stories
from src.graphs.nodes.script_generation import (
    prepare_story_payload,
    generate_script,
    assess_script,
    mark_manual_review,
    finalize_script,
)
from src.graphs.checkpoints import get_default_checkpointer

class UnifiedState(TypedDict):
    """Unified state for all pipeline stages."""
    # Stage 1: Research
    request_id: str
    sources: Optional[List[Dict]]
    raw_stories: Optional[List[Dict]]
    enriched_stories: Optional[List[Dict]]
    scored_stories: Optional[List[Dict]]
    selected_stories: Optional[List[Dict]]
    companies: Optional[List[str]]
    scoring_weights: Optional[Dict]
    trending_keywords: Optional[List[str]]
    hours_filter: Optional[int]
    diagnostics: Optional[Dict]
    errors: Optional[List[str]]
    checkpoints: Optional[Dict]
    metadata: Optional[Dict]
    
    # Stage 2: Script
    story_payload: Optional[Dict]
    script_draft: Optional[Dict]
    validation: Optional[Dict]
    manual_review: Optional[bool]
    final_script: Optional[Dict]

def create_unified_visual_graph():
    """Create a visual graph showing all stages connected."""
    graph = StateGraph(UnifiedState)
    
    # Stage 1: Research nodes
    graph.add_node("load_metadata", load_metadata)
    graph.add_node("fetch_feeds", fetch_feeds)
    graph.add_node("merge", merge_sources)
    graph.add_node("enrich", enrich_stories)
    graph.add_node("score", score_stories)
    graph.add_node("select", select_stories)
    
    # Stage 2: Script nodes
    graph.add_node("prepare_script", prepare_story_payload)
    graph.add_node("generate_script", generate_script)
    graph.add_node("manual_review", mark_manual_review)
    graph.add_node("finalize_script", finalize_script)
    
    # Set entry point
    graph.set_entry_point("load_metadata")
    
    # Stage 1 flow
    graph.add_edge("load_metadata", "fetch_feeds")
    graph.add_edge("fetch_feeds", "merge")
    graph.add_edge("merge", "enrich")
    graph.add_edge("enrich", "score")
    graph.add_edge("score", "select")
    
    # Connect Stage 1 to Stage 2
    graph.add_edge("select", "prepare_script")
    
    # Stage 2 flow
    graph.add_edge("prepare_script", "generate_script")
    graph.add_conditional_edges(
        "generate_script",
        assess_script,
        {
            "accept": "finalize_script",
            "retry": "generate_script",
            "manual": "manual_review",
        },
    )
    graph.add_edge("manual_review", "finalize_script")
    graph.add_edge("finalize_script", END)
    
    # Add checkpointer
    checkpointer = get_default_checkpointer("unified_visual")
    return graph.compile(checkpointer=checkpointer)

# Export for LangGraph
build_unified_visual_graph = create_unified_visual_graph
