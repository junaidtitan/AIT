#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REQUIREMENTS_FILE="$ROOT_DIR/requirements/langgraph.lock"
ENV_TEMPLATE="$ROOT_DIR/.env.langgraph"

if [[ ! -f "$REQUIREMENTS_FILE" ]]; then
  echo "[bootstrap] requirements file not found: $REQUIREMENTS_FILE" >&2
  exit 1
fi

echo "[bootstrap] Installing LangGraph dependencies..."
python3 -m pip install --upgrade pip >/dev/null
python3 -m pip install --requirement "$REQUIREMENTS_FILE"

echo "[bootstrap] Ensuring LangGraph environment template..."
if [[ ! -f "$ENV_TEMPLATE" ]]; then
  cat <<'TPL' > "$ENV_TEMPLATE"
# Environment variables for LangGraph integration
# Copy to .env or export in your shell before running the LangGraph pipeline.
LANGCHAIN_TRACING_V2=false
LANGGRAPH_STUDIO_TOKEN=
LANGGRAPH_PROJECT=junaidq-ai-news
LANGGRAPH_CHECKPOINT_DIR=.langgraph/checkpoints
LANGGRAPH_MAX_CONCURRENCY=4
LANGGRAPH_NODE_TIMEOUT=30
LANGGRAPH_RETRY_BACKOFF=1.5
TPL
  echo "[bootstrap] Created $ENV_TEMPLATE"
else
  echo "[bootstrap] Template already exists at $ENV_TEMPLATE"
fi

echo "[bootstrap] LangGraph bootstrap completed."
