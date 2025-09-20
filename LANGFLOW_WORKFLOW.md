# Langflow → LangGraph Workflow

This repository now treats Langflow as the **visual editor** for the pipeline while the codebase remains the canonical implementation. The loop works like this:

1. Langflow components (`AITPipelineNode`) describe real pipeline nodes.
2. You edit and wire them visually in the Langflow UI.
3. `sync_langflow_changes.py` pulls the flow, validates it, and rewrites `langflow/pipeline_config.json`.
4. `src/unified_visual_pipeline.py` reads that config and builds the executable LangGraph.

## Prerequisites

- Langflow running locally (e.g. `bash langflow_setup.sh`; default URL `http://localhost:7860`).
- Secrets available via Secret Manager (`SHEETS_SERVICE_ACCOUNT`, `YOUTUBE_API_KEY`, `OPENAI_API_KEY`).
- Optional: exported flow JSON if you prefer offline sync (`langflow_flows/latest_flow.json`).

## Editing Workflow

1. Launch Langflow and load the latest config
   - Import `langflow_flows/latest_flow.json` **or** start from scratch using the `AITPipelineNode` component.
   - Each node exposes a dropdown with the supported pipeline components (`load_metadata`, `generate_script`, etc.).
2. Edit the flow visually (add/remove nodes, rewire edges). The component’s *ID* should remain unique.
3. When you’re ready to publish the change:
   ```bash
   python sync_langflow_changes.py          # pull from http://localhost:7860
   # or
   python sync_langflow_changes.py --flow-file /path/to/export.json
   ```
   The script will:
   - Acquire a lock (`langflow/.edit.lock`) so concurrent edits don’t collide.
   - Store the raw export under `langflow_flows/latest_flow.json` (timestamped copies as well).
   - Convert the flow to `langflow/pipeline_config.json` and run a compile check against LangGraph.
4. Commit the updated config (and any flow exports you want to version) just like regular code.

## Validations & Locking

- `langflow_support/schema.py` enforces schema rules (unique nodes, valid edges, etc.).
- `langflow_support/validator.py` compiles the graph; use it locally or in CI:
  ```bash
  python -m langflow_support.validator
  ```
- The lock file prevents double-syncs; if you see `Langflow edit lock already held…` confirm no one else is mid-sync, then remove the lock if safe.

## Configuration Files

- `langflow/pipeline_config.json` — canonical pipeline wiring (committed).
- `langflow_flows/latest_flow.json` — most recent raw export (optional to commit, but helpful for diffing).
- `langflow_components/ait_stages.py` — defines the minimal Langflow component used in the UI.

## Running the Pipeline

`src/unified_visual_pipeline.py` now reads the config automatically:
```python
from langflow_support import build_graph_from_file
graph = build_graph_from_file("langflow/pipeline_config.json")
```
That means any validated Langflow edits are respected by the production pipeline without touching the rest of the code.

## CI Recommendation

Add a workflow (example `.github/workflows/langflow.yml`):
```yaml
name: Langflow Pipeline Check
on: [push, pull_request]
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - run: pip install -r requirements/langgraph.lock
      - run: python -m langflow_support.validator
```

## Common Questions

**What happens if the Langflow UI crashes mid-edit?**
Nothing changes in code until you run `sync_langflow_changes.py`. The canonical config remains untouched.

**Can I run the pipeline without Langflow?**
Yes. The config is code-driven; Langflow is just a visual editor. `python3 -m src.unified_langgraph_pipeline` works as before.

**How do I revert a bad visual edit?**
Git revert the commit that changed `langflow/pipeline_config.json` (and optionally the stored flow JSON), then rerun the pipeline.

**How do I add new components?**
1. Add a new entry to `langflow_components/ait_stages.py` (and the registry in `langflow_support/component_registry.py`).
2. Document the component key so Langflow users can select it.
3. Run the sync workflow and tests to ensure it compiles.
