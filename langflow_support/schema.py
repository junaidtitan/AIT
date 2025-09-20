"""Pydantic models representing the sanitized Langflow pipeline configuration."""

from __future__ import annotations

from typing import Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class NodeConfig(BaseModel):
    """Represents a single pipeline node."""

    id: str = Field(..., description="Unique node identifier used in the graph")
    component: str = Field(..., description="Registry key for the node implementation")
    params: Dict[str, object] = Field(default_factory=dict, description="Optional static parameter overrides")


class EdgeConfig(BaseModel):
    """Represents a directed edge between two nodes."""

    source: str = Field(..., description="Outgoing node identifier")
    target: str = Field(..., description="Incoming node identifier")


class ConditionalRouteConfig(BaseModel):
    """Represents a conditional router mapping."""

    source: str = Field(..., description="Node identifier that emits the routing signal")
    router: str = Field(..., description="Component key for the router callable")
    routes: Dict[str, str] = Field(..., description="Mapping from router output to downstream node ids")


class PipelineMetadata(BaseModel):
    """Top-level metadata for the pipeline."""

    name: str = Field(..., description="Human readable pipeline name")
    state: str = Field(..., description="Registry key for the state model")
    entry_point: str = Field(..., description="Identifier of the entry node")
    checkpointer_id: Optional[str] = Field(None, description="Identifier passed to checkpointer factory")


class PipelineConfig(BaseModel):
    """Canonical representation of the Langflow-authored pipeline."""

    pipeline: PipelineMetadata
    nodes: List[NodeConfig]
    edges: List[EdgeConfig]
    conditional_edges: List[ConditionalRouteConfig] = Field(default_factory=list)
    end_nodes: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_model(self) -> "PipelineConfig":  # noqa: D401
        node_ids = [node.id for node in self.nodes]
        duplicate_ids = {node_id for node_id in node_ids if node_ids.count(node_id) > 1}
        if duplicate_ids:
            raise ValueError(f"Duplicate node identifiers detected: {sorted(duplicate_ids)}")

        node_id_set = set(node_ids)
        for edge in self.edges:
            if edge.source not in node_id_set:
                raise ValueError(f"Edge source '{edge.source}' does not reference a known node")
            if edge.target not in node_id_set:
                raise ValueError(f"Edge target '{edge.target}' does not reference a known node")

        for route in self.conditional_edges:
            if route.source not in node_id_set:
                raise ValueError(f"Conditional router source '{route.source}' is not a known node")
            for target in route.routes.values():
                if target not in node_id_set:
                    raise ValueError(
                        f"Conditional router '{route.router}' maps to unknown node '{target}'"
                    )

        for node_id in self.end_nodes:
            if node_id not in node_id_set:
                raise ValueError(f"End node '{node_id}' does not reference a known node")

        if self.pipeline.entry_point not in node_id_set:
            raise ValueError(
                f"Entry point '{self.pipeline.entry_point}' is not defined amongst nodes"
            )

        return self

    def node_map(self) -> Dict[str, NodeConfig]:
        """Return a convenience dictionary mapping node ids to configs."""

        return {node.id: node for node in self.nodes}
