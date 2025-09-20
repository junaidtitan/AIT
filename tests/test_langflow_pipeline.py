"""Tests for Langflow configuration tooling."""

from __future__ import annotations

from pathlib import Path

import pytest

from langflow_support.builder import build_graph_from_file, build_graph_from_config
from langflow_support.parser import parse_flow_export
from langflow_support.schema import PipelineConfig


FIXTURE_DIR = Path("langflow")
CONFIG_PATH = FIXTURE_DIR / "pipeline_config.json"


@pytest.mark.parametrize("config_path", [CONFIG_PATH])
def test_pipeline_config_compiles(config_path: Path) -> None:
    graph = build_graph_from_file(config_path)
    assert graph is not None


def test_parse_flow_export_generates_config() -> None:
    flow_export = {
        "name": "AIT Unified Pipeline",
        "data": {
            "nodes": [
                {"id": "load_metadata", "data": {"component_class": "AITPipelineNode", "value": {"component": "load_metadata"}}},
                {"id": "fetch_feeds", "data": {"component_class": "AITPipelineNode", "value": {"component": "fetch_feeds"}}},
            ],
            "edges": [
                {"source": "load_metadata", "target": "fetch_feeds"},
            ],
        },
    }
    config = parse_flow_export(flow_export)
    assert isinstance(config, PipelineConfig)
    assert config.pipeline.entry_point == "load_metadata"
    assert {node.id for node in config.nodes} == {"load_metadata", "fetch_feeds"}

    graph = build_graph_from_config(config)
    assert graph is not None
