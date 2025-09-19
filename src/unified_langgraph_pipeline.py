"""CLI entrypoint for running the LangGraph pipeline."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from typing import Tuple

from langgraph.graph import END, StateGraph

from src.graphs import build_research_graph, build_script_graph
from src.graphs.state import ResearchState, ScriptState


def create_unified_graph():
    """Create a unified graph for LangGraph dev server."""
    graph = StateGraph(dict)

    async def run_unified(state):
        research_graph = build_research_graph()
        script_graph = build_script_graph()

        research_state = ResearchState(
            hours_filter=state.get("hours_filter"),
            metadata={"selection_limit": state.get("selection_limit", 6)},
        )
        base_thread_id = state.get("thread_id") or research_state.request_id
        research_config = {
            "configurable": {
                "thread_id": f"{base_thread_id}-research",
            }
        }
        research_raw = await research_graph.ainvoke(research_state, config=research_config)
        research_result = research_raw if isinstance(research_raw, ResearchState) else ResearchState.model_validate(research_raw)

        script_state = ScriptState(
            selected_stories=research_result.selected_stories,
            metadata={"max_attempts": state.get("max_attempts", 2)},
        )
        script_config = {
            "configurable": {
                "thread_id": f"{base_thread_id}-script",
            }
        }
        script_raw = await script_graph.ainvoke(script_state, config=script_config)
        script_result = script_raw if isinstance(script_raw, ScriptState) else ScriptState.model_validate(script_raw)

        return {
            "research": research_result,
            "script": script_result,
            "final_text": script_result.final_script.final_text if script_result.final_script else None,
        }

    graph.add_node("pipeline", run_unified)
    graph.set_entry_point("pipeline")
    graph.add_edge("pipeline", END)

    return graph.compile()


async def run_pipeline(
    hours_filter: int | None = None,
    selection_limit: int = 6,
    max_attempts: int = 2,
    thread_id: str | None = None,
) -> Tuple[ResearchState, ScriptState]:
    research_graph = build_research_graph()
    research_state = ResearchState(
        hours_filter=hours_filter,
        metadata={"selection_limit": selection_limit},
    )
    base_thread_id = thread_id or research_state.request_id
    research_config = {
        "configurable": {
            "thread_id": f"{base_thread_id}-research",
        }
    }
    research_raw = await research_graph.ainvoke(
        research_state, config=research_config
    )
    research_result = research_raw if isinstance(research_raw, ResearchState) else ResearchState.model_validate(research_raw)
    script_graph = build_script_graph()
    script_state = ScriptState(
        selected_stories=research_result.selected_stories,
        metadata={"max_attempts": max_attempts},
    )
    script_config = {
        "configurable": {
            "thread_id": f"{base_thread_id}-script",
        }
    }
    script_raw = await script_graph.ainvoke(script_state, config=script_config)
    script_result = script_raw if isinstance(script_raw, ScriptState) else ScriptState.model_validate(script_raw)
    return research_result, script_result


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the LangGraph AI news pipeline")
    parser.add_argument("--hours-filter", type=int, default=None, help="Limit stories to the last N hours")
    parser.add_argument("--selection-limit", type=int, default=6, help="Number of stories to select")
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=2,
        help="Maximum script generation attempts before manual review",
    )
    parser.add_argument("--thread-id", type=str, default=None, help="Thread identifier for checkpointing")
    parser.add_argument("--output", type=Path, default=None, help="Optional path to dump script text")
    args = parser.parse_args()
    research_state, script_state = asyncio.run(
        run_pipeline(
            hours_filter=args.hours_filter,
            selection_limit=args.selection_limit,
            max_attempts=args.max_attempts,
            thread_id=args.thread_id,
        )
    )
    print("Research diagnostics:", research_state.diagnostics.events)
    if script_state.final_script:
        msg = "\nGenerated script (validation score {:.2f}):".format(
            script_state.final_script.validation.score
        )
        print(msg)
        preview = script_state.final_script.final_text or ""
        print(preview[:400] if preview else "[empty]")
        if args.output and preview:
            args.output.write_text(preview, encoding="utf-8")
            print(f"Saved script to {args.output}")
    else:
        print("Script generation failed", script_state.errors)
    if script_state.manual_review:
        print("\n⚠️ Manual review required before publishing.")


if __name__ == "__main__":
    main()
