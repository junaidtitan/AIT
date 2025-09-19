#!/usr/bin/env python3
"""Simple web interface for monitoring LangGraph pipeline execution."""

import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from src.unified_langgraph_pipeline import run_pipeline
from src.graphs.checkpoints import FileCheckpointSaver

app = FastAPI(title="LangGraph Pipeline Monitor")

class PipelineRequest(BaseModel):
    hours_filter: Optional[int] = 24
    selection_limit: int = 6
    max_attempts: int = 2
    thread_id: Optional[str] = None

class PipelineStatus(BaseModel):
    status: str
    thread_id: str
    research_complete: bool
    script_complete: bool
    errors: List[str]
    timestamp: str

@app.get("/", response_class=HTMLResponse)
async def home():
    """Simple dashboard HTML."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>LangGraph Pipeline Monitor</title>
        <style>
            body { font-family: Arial; max-width: 1200px; margin: 0 auto; padding: 20px; }
            .status { padding: 10px; margin: 10px 0; border-radius: 5px; }
            .running { background: #fff3cd; }
            .complete { background: #d4edda; }
            .error { background: #f8d7da; }
            button { padding: 10px 20px; margin: 5px; cursor: pointer; }
            pre { background: #f4f4f4; padding: 10px; overflow-x: auto; }
        </style>
    </head>
    <body>
        <h1>🚀 LangGraph Pipeline Monitor</h1>

        <div>
            <h2>Run Pipeline</h2>
            <button onclick="runPipeline()">Start New Pipeline Run</button>
            <button onclick="getStatus()">Check Status</button>
        </div>

        <div id="status"></div>
        <div id="result"></div>

        <script>
            async function runPipeline() {
                const status = document.getElementById('status');
                status.innerHTML = '<div class="status running">Starting pipeline...</div>';

                const response = await fetch('/run', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        hours_filter: 24,
                        selection_limit: 6,
                        max_attempts: 2
                    })
                });

                const data = await response.json();
                document.getElementById('result').innerHTML =
                    '<pre>' + JSON.stringify(data, null, 2) + '</pre>';
            }

            async function getStatus() {
                const response = await fetch('/status');
                const data = await response.json();

                const statusDiv = document.getElementById('status');
                const cssClass = data.script_complete ? 'complete' : 'running';
                statusDiv.innerHTML = `
                    <div class="status ${cssClass}">
                        <strong>Status:</strong> ${data.status}<br>
                        <strong>Thread:</strong> ${data.thread_id}<br>
                        <strong>Research:</strong> ${data.research_complete ? '✅' : '⏳'}<br>
                        <strong>Script:</strong> ${data.script_complete ? '✅' : '⏳'}<br>
                        <strong>Time:</strong> ${data.timestamp}
                    </div>
                `;
            }
        </script>
    </body>
    </html>
    """
    return html

@app.post("/run")
async def run_pipeline_endpoint(request: PipelineRequest):
    """Execute the LangGraph pipeline."""
    try:
        research_state, script_state = await run_pipeline(
            hours_filter=request.hours_filter,
            selection_limit=request.selection_limit,
            max_attempts=request.max_attempts,
            thread_id=request.thread_id
        )

        return {
            "success": True,
            "thread_id": research_state.request_id,
            "research": {
                "stories_found": len(research_state.raw_stories),
                "stories_selected": len(research_state.selected_stories),
                "diagnostics": research_state.diagnostics.events
            },
            "script": {
                "generated": script_state.final_script is not None,
                "validation_score": script_state.final_script.validation.score if script_state.final_script else 0,
                "manual_review": script_state.manual_review,
                "attempts": script_state.attempts
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status")
async def get_status():
    """Get current pipeline status from checkpoints."""
    checkpoint_dir = Path(".langgraph/checkpoints")

    # Find most recent checkpoint
    latest_thread = None
    latest_time = None

    if checkpoint_dir.exists():
        for path in checkpoint_dir.glob("*/*.json"):
            if latest_time is None or path.stat().st_mtime > latest_time:
                latest_time = path.stat().st_mtime
                latest_thread = path.stem

    if latest_thread:
        research_done = (checkpoint_dir / "research" / f"{latest_thread}.json").exists()
        script_done = (checkpoint_dir / "script" / f"{latest_thread}.json").exists()

        return PipelineStatus(
            status="complete" if script_done else "running",
            thread_id=latest_thread,
            research_complete=research_done,
            script_complete=script_done,
            errors=[],
            timestamp=datetime.fromtimestamp(latest_time).isoformat()
        )

    return PipelineStatus(
        status="no_runs",
        thread_id="",
        research_complete=False,
        script_complete=False,
        errors=[],
        timestamp=datetime.now().isoformat()
    )

@app.get("/checkpoints/{workflow}")
async def list_checkpoints(workflow: str):
    """List all checkpoints for a workflow."""
    checkpoint_dir = Path(f".langgraph/checkpoints/{workflow}")

    if not checkpoint_dir.exists():
        return []

    checkpoints = []
    for path in checkpoint_dir.glob("*.json"):
        checkpoints.append({
            "thread_id": path.stem,
            "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
            "size": path.stat().st_size
        })

    return sorted(checkpoints, key=lambda x: x["modified"], reverse=True)

if __name__ == "__main__":
    import uvicorn
    print("🌐 Starting LangGraph Monitor on http://localhost:8000")
    print("📡 Access from your local machine if using SSH port forwarding")
    uvicorn.run(app, host="0.0.0.0", port=8000)