"""Registry that maps Langflow component identifiers to callable pipeline functions."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Callable, Dict, Optional



@dataclass(frozen=True)
class PipelineComponent:
    """Metadata for a pipeline component."""

    dotted_path: str
    kind: str = "node"  # "node" or "router"

    def load(self) -> Callable:
        module_path, _, attribute = self.dotted_path.rpartition(".")
        if not module_path:
            raise ValueError(f"Invalid dotted path '{self.dotted_path}'")
        module = importlib.import_module(module_path)
        try:
            return getattr(module, attribute)
        except AttributeError as exc:  # pragma: no cover - defensive
            raise RuntimeError(
                f"Component '{self.dotted_path}' could not be imported"
            ) from exc


COMPONENT_REGISTRY: Dict[str, PipelineComponent] = {
    "load_metadata": PipelineComponent("src.graphs.nodes.fetchers.load_sheet_metadata"),
    "fetch_feeds": PipelineComponent("src.graphs.nodes.fetchers.fetch_story_feeds"),
    "merge_stories": PipelineComponent("src.graphs.nodes.mergers.merge_and_dedupe"),
    "enrich_stories": PipelineComponent("src.graphs.nodes.enrichers.enrich_stories"),
    "score_stories": PipelineComponent("src.graphs.nodes.rankers.score_stories"),
    "select_stories": PipelineComponent("src.graphs.nodes.rankers.select_top_stories"),
    "prepare_script": PipelineComponent("src.graphs.nodes.script_generation.prepare_story_payload"),
    "generate_script": PipelineComponent("src.graphs.nodes.script_generation.generate_script"),
    "manual_review": PipelineComponent("src.graphs.nodes.script_generation.mark_manual_review"),
    "finalize_script": PipelineComponent("src.graphs.nodes.script_generation.finalize_script"),
    "assess_script": PipelineComponent("src.graphs.nodes.script_generation.assess_script", kind="router"),
}

STATE_REGISTRY: Dict[str, str] = {
    "ResearchState": "src.graphs.state.ResearchState",
    "ScriptState": "src.graphs.state.ScriptState",
    "UnifiedPipelineState": "src.unified_visual_pipeline.UnifiedPipelineState",
}


def resolve_component(component_key: str) -> PipelineComponent:
    try:
        return COMPONENT_REGISTRY[component_key]
    except KeyError as exc:
        raise KeyError(f"Unknown component '{component_key}'") from exc


def resolve_state(state_key: str) -> type:
    try:
        dotted_path = STATE_REGISTRY[state_key]
    except KeyError as exc:
        raise KeyError(f"Unknown pipeline state '{state_key}'") from exc

    module_path, _, attribute = dotted_path.rpartition('.')
    module = importlib.import_module(module_path)
    try:
        return getattr(module, attribute)
    except AttributeError as exc:  # pragma: no cover - defensive
        raise RuntimeError(
            f"State '{dotted_path}' could not be imported"
        ) from exc

