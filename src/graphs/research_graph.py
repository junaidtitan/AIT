"""Research graph assembly."""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from src.graphs.checkpoints import get_default_checkpointer
from src.graphs.nodes.enrichers import enrich_stories
from src.graphs.nodes.fetchers import fetch_story_feeds, load_sheet_metadata
from src.graphs.nodes.mergers import merge_and_dedupe
from src.graphs.nodes.rankers import score_stories, select_top_stories
from src.graphs.state import ResearchState


def build_research_graph() -> StateGraph:
    graph = StateGraph(ResearchState)
    graph.add_node("load_metadata", load_sheet_metadata)
    graph.add_node("fetch_feeds", fetch_story_feeds)
    graph.add_node("merge", merge_and_dedupe)
    graph.add_node("enrich", enrich_stories)
    graph.add_node("score", score_stories)
    graph.add_node("select", select_top_stories)
    graph.set_entry_point("load_metadata")
    graph.add_edge("load_metadata", "fetch_feeds")
    graph.add_edge("fetch_feeds", "merge")
    graph.add_edge("merge", "enrich")
    graph.add_edge("enrich", "score")
    graph.add_edge("score", "select")
    graph.add_edge("select", END)
    checkpointer = get_default_checkpointer("research")
    return graph.compile(checkpointer=checkpointer)
