"""Parse Langflow flow exports into sanitized PipelineConfig objects."""

from __future__ import annotations

from typing import Dict, Any, Iterable, Set

from .component_registry import COMPONENT_REGISTRY
from .schema import (
    PipelineConfig,
    PipelineMetadata,
    NodeConfig,
    EdgeConfig,
    ConditionalRouteConfig,
)

DEFAULT_CONDITIONAL = ConditionalRouteConfig(
    source="generate",
    router="assess_script",
    routes={
        "accept": "finalize",
        "retry": "generate",
        "manual": "manual_review",
    },
)

DEFAULT_END_NODE = "finalize"


def _iter_nodes(flow_data: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    nodes = flow_data.get("nodes")
    if nodes is None and "data" in flow_data:
        nodes = flow_data["data"].get("nodes")
    return nodes or []


def _iter_edges(flow_data: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    edges = flow_data.get("edges")
    if edges is None and "data" in flow_data:
        edges = flow_data["data"].get("edges")
    return edges or []


def _normalise_node(node: Dict[str, Any]) -> NodeConfig:
    node_id = node.get("id")
    if node_id is None:
        raise ValueError("Langflow node is missing an identifier")

    data = node.get("data", {})
    value_block = data.get("value") or {}
    component_key = value_block.get("component") or node_id
    params = value_block.get("params") or {}

    if component_key not in COMPONENT_REGISTRY:
        raise ValueError(
            f"Node '{node_id}' references unknown component '{component_key}'"
        )

    if not isinstance(params, dict):
        params = {}

    return NodeConfig(id=node_id, component=component_key, params=params)


def parse_flow_export(flow_json: Dict[str, Any]) -> PipelineConfig:
    """Convert Langflow's export JSON into PipelineConfig."""

    flow_data = flow_json.get("data") or flow_json
    node_map = {}
    for raw_node in _iter_nodes(flow_data):
        node_config = _normalise_node(raw_node)
        node_map[node_config.id] = node_config

    if not node_map:
        raise ValueError("Flow export contained no nodes")

    edges = [EdgeConfig(source=edge["source"], target=edge["target"]) for edge in _iter_edges(flow_data)]

    incoming: Set[str] = {edge.target for edge in edges}
    entry_candidates = [node_id for node_id in node_map if node_id not in incoming]
    entry_point = entry_candidates[0] if entry_candidates else next(iter(node_map))

    metadata = PipelineMetadata(
        name=flow_json.get("name", "langflow_pipeline"),
        state="UnifiedPipelineState",
        entry_point=entry_point,
        checkpointer_id="unified_pipeline",
    )

    conditional_edges = []
    if {"generate", "finalize", "manual_review"}.issubset(node_map):
        conditional_edges.append(DEFAULT_CONDITIONAL)

    end_nodes = [DEFAULT_END_NODE] if DEFAULT_END_NODE in node_map else []

    return PipelineConfig(
        pipeline=metadata,
        nodes=list(node_map.values()),
        edges=edges,
        conditional_edges=conditional_edges,
        end_nodes=end_nodes,
    )
