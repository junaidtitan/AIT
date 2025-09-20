"""Utility for validating that the Langflow configuration compiles."""

from __future__ import annotations

from pathlib import Path

from .builder import build_graph_from_file


def validate_pipeline(config_path: Path | str = "langflow/pipeline_config.json") -> None:
    build_graph_from_file(config_path)


if __name__ == "__main__":
    validate_pipeline()
    print("Langflow pipeline configuration is valid ✅")
