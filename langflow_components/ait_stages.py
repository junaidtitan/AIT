"""Lightweight Langflow components describing the production pipeline nodes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any

from langflow.custom import CustomComponent
from langflow.field_typing import Data, Text


@dataclass(frozen=True)
class ComponentDescriptor:
    """Metadata representing a pipeline node."""

    key: str
    display_name: str
    description: str


COMPONENTS = [
    ComponentDescriptor("load_metadata", "Research · Load Metadata", "Load configuration from Google Sheets"),
    ComponentDescriptor("fetch_feeds", "Research · Fetch Feeds", "Ingest articles from configured feeds"),
    ComponentDescriptor("merge_stories", "Research · Merge Stories", "Merge and deduplicate feed results"),
    ComponentDescriptor("enrich_stories", "Research · Enrich Stories", "Run story enrichment pipeline"),
    ComponentDescriptor("score_stories", "Research · Score Stories", "Score stories for prioritisation"),
    ComponentDescriptor("select_stories", "Research · Select Stories", "Select top stories for scripting"),
    ComponentDescriptor("prepare_script", "Script · Prepare Payload", "Prepare data for script generation"),
    ComponentDescriptor("generate_script", "Script · Generate", "Generate draft script"),
    ComponentDescriptor("manual_review", "Script · Manual Review", "Flag script for manual review"),
    ComponentDescriptor("finalize_script", "Script · Finalize", "Finalize the script artifact"),
    ComponentDescriptor("assess_script", "Router · Assess Script", "Route script generation outcomes"),
]

_COMPONENT_OPTIONS = [descriptor.key for descriptor in COMPONENTS]
_DESCRIPTOR_BY_KEY = {descriptor.key: descriptor for descriptor in COMPONENTS}


class AITPipelineNode(CustomComponent):
    """Generic pipeline node used purely for configuration."""

    display_name = "AIT Pipeline Node"
    description = "Represents a pipeline stage; output is consumed by the sync tooling."

    def build_config(self) -> dict:
        return {
            "component_key": {
                "display_name": "Pipeline Component",
                "options": _COMPONENT_OPTIONS,
                "value": _COMPONENT_OPTIONS[0],
            },
            "notes": {
                "display_name": "Notes",
                "field_type": "str",
                "value": "",
                "info": "Optional context only stored in Langflow",
            },
        }

    def build(self, component_key: str, notes: Text) -> Data:
        descriptor = _DESCRIPTOR_BY_KEY.get(component_key)
        if descriptor is None:
            raise ValueError(f"Unknown pipeline component '{component_key}'")
        payload: Dict[str, Any] = {
            "component": descriptor.key,
            "notes": notes,
        }
        return Data(value=payload)
