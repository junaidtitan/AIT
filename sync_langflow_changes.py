#!/usr/bin/env python3
"""Synchronise Langflow edits into the canonical pipeline configuration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

import requests

from langflow_support.lock import langflow_lock
from langflow_support.parser import parse_flow_export
from langflow_support.validator import validate_pipeline
from langflow_support.schema import PipelineConfig

FLOW_EXPORT_DIR = Path("langflow_flows")
DEFAULT_CONFIG_PATH = Path("langflow/pipeline_config.json")


def _fetch_flow_from_api(base_url: str) -> dict:
    response = requests.get(f"{base_url.rstrip('/')}/api/v1/flows")
    response.raise_for_status()
    flows = response.json().get("flows", [])
    if not flows:
        raise RuntimeError("No flows available from Langflow API")
    return flows[0]


def _load_flow_json(path: Path) -> dict:
    return json.loads(path.read_text())


def _persist_export(flow: dict, export_dir: Path) -> None:
    export_dir.mkdir(parents=True, exist_ok=True)
    export_path = export_dir / "latest_flow.json"
    export_path.write_text(json.dumps(flow, indent=2))
    print(f"✅ Stored raw flow export at {export_path}")


def sync(flow: dict, config_path: Path = DEFAULT_CONFIG_PATH) -> PipelineConfig:
    config = parse_flow_export(flow)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(config.model_dump_json(indent=2))
    print(f"✅ Wrote canonical pipeline config to {config_path}")
    validate_pipeline(config_path)
    print("✅ Configuration validated via LangGraph compile")
    return config


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync Langflow changes into the repo")
    parser.add_argument(
        "--flow-file",
        type=Path,
        help="Path to a Langflow JSON export (overrides API call)",
    )
    parser.add_argument(
        "--api-url",
        default="http://localhost:7860",
        help="Langflow base URL (used when --flow-file is not provided)",
    )
    parser.add_argument(
        "--lock-timeout",
        type=float,
        default=5.0,
        help="Seconds to wait for Langflow sync lock",
    )
    args = parser.parse_args()

    if args.flow_file:
        flow_json = _load_flow_json(args.flow_file)
    else:
        flow_json = _fetch_flow_from_api(args.api_url)

    with langflow_lock(timeout=args.lock_timeout):
        _persist_export(flow_json, FLOW_EXPORT_DIR)
        sync(flow_json, DEFAULT_CONFIG_PATH)

    print("✨ Langflow pipeline synchronised successfully")


if __name__ == "__main__":
    main()
