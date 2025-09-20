"""Utilities to build LangGraph graphs from sanitized Langflow configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Callable, Any
from functools import partial
import inspect

from langgraph.graph import StateGraph, END

from src.graphs.checkpoints import get_default_checkpointer

from .component_registry import resolve_component, resolve_state
from .schema import PipelineConfig, NodeConfig


def _wrap_callable(func: Callable, params: Dict[str, Any]) -> Callable:
    """Return a callable with params applied if provided."""

    if not params:
        return func

    if inspect.iscoroutinefunction(func):

        async def _async_wrapper(state):
            return await func(state=state, **params)

        return _async_wrapper

    def _sync_wrapper(state):
        return func(state=state, **params)

    return _sync_wrapper


def build_graph_from_config(config: PipelineConfig) -> StateGraph:
    """Build and compile a StateGraph from a PipelineConfig."""

    state_cls = resolve_state(config.pipeline.state)
    graph = StateGraph(state_cls)

    for node in config.nodes:
        component = resolve_component(node.component)
        callable_obj = component.load()
        graph.add_node(node.id, _wrap_callable(callable_obj, node.params))

    for edge in config.edges:
        graph.add_edge(edge.source, edge.target)

    for conditional in config.conditional_edges:
        router_component = resolve_component(conditional.router)
        router_callable = router_component.load()
        graph.add_conditional_edges(
            conditional.source,
            router_callable,
            conditional.routes,
        )

    for end_node in config.end_nodes:
        graph.add_edge(end_node, END)

    graph.set_entry_point(config.pipeline.entry_point)
    checkpointer_id = config.pipeline.checkpointer_id or config.pipeline.name
    compiled = graph.compile(checkpointer=get_default_checkpointer(checkpointer_id))
    return compiled


def build_graph_from_file(config_path: Path | str) -> StateGraph:
    """Load a PipelineConfig from disk and compile the graph."""

    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Pipeline config not found at {path}")
    config = PipelineConfig.model_validate_json(path.read_text())
    return build_graph_from_config(config)
