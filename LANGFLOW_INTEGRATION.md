# Langflow Integration Overview

Langflow is used as a **visual editor** for the LangGraph pipeline. The key pieces are:

- `langflow_components/ait_stages.py` — custom components surfaced inside Langflow.
- `sync_langflow_changes.py` — CLI that exports the current flow, validates it, and writes the canonical config (`langflow/pipeline_config.json`).
- `langflow_support/` — shared tooling that parses flows, manages locks, and compiles the graph.

For the full workflow (starting the UI, syncing changes, validation, CI), see [`LANGFLOW_WORKFLOW.md`](LANGFLOW_WORKFLOW.md).
