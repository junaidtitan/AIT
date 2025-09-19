"""Script generation graph."""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from src.graphs.checkpoints import get_default_checkpointer
from src.graphs.nodes.script_generation import (
    finalize_script,
    generate_script,
    mark_manual_review,
    prepare_story_payload,
    assess_script,
)
from src.graphs.state import ScriptState


def build_script_graph() -> StateGraph:
    graph = StateGraph(ScriptState)
    graph.add_node("prepare", prepare_story_payload)
    graph.add_node("generate", generate_script)
    graph.add_node("manual_review", mark_manual_review)
    graph.add_node("finalize", finalize_script)
    graph.set_entry_point("prepare")
    graph.add_edge("prepare", "generate")
    graph.add_conditional_edges(
        "generate",
        assess_script,
        {
            "accept": "finalize",
            "retry": "generate",
            "manual": "manual_review",
        },
    )
    graph.add_edge("manual_review", "finalize")
    graph.add_edge("finalize", END)
    checkpointer = get_default_checkpointer("script")
    return graph.compile(checkpointer=checkpointer)
