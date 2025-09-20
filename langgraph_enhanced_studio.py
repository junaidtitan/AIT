#!/usr/bin/env python3
"""
Enhanced LangGraph Studio - Production-Grade Visual Pipeline Development
Features: Real-time editing, flow visualization, LLM tracking, and debugging
"""

import os
import sys
import json
import time
import asyncio
import inspect
from typing import Dict, List, Any, Optional, Callable, TypedDict
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field
import traceback

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.pregel import Channel
from langsmith import Client as LangSmithClient
from langsmith.schemas import Run, Example
import pandas as pd
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel

console = Console()


class PipelineState(TypedDict):
    """Enhanced state with comprehensive tracking"""
    current_stage: str
    stages_completed: List[str]
    stage_outputs: Dict[str, Any]
    llm_traces: List[Dict]
    execution_timeline: List[Dict]
    errors: List[Dict]
    metrics: Dict[str, Any]
    context: Dict[str, Any]
    checkpoints: List[Dict]


@dataclass
class LLMTrace:
    """Detailed LLM call trace"""
    id: str
    stage: str
    timestamp: datetime
    model: str
    provider: str
    config: Dict[str, Any]
    messages: List[Dict]
    response: str
    usage: Dict[str, int]
    latency_ms: float
    cost_usd: float
    metadata: Dict = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class StageDefinition:
    """Complete stage definition with code and config"""
    name: str
    description: str
    code: str  # Actual Python code
    dependencies: List[str]
    llm_configs: List[Dict[str, Any]]  # Multiple LLM calls per stage
    retry_config: Dict[str, Any]
    timeout_seconds: int
    validation_rules: List[str]
    test_cases: List[Dict]


class EnhancedLangGraphStudio:
    """Production-ready LangGraph development studio"""

    def __init__(self, project_name: str = "langgraph_project"):
        self.project_name = project_name
        self.stages: Dict[str, StageDefinition] = {}
        self.graph: Optional[StateGraph] = None
        self.compiled_graph = None
        self.llm_traces: List[LLMTrace] = []
        self.execution_history: List[Dict] = []

        # Initialize tracking
        self.langsmith_client = None
        self.init_langsmith()

        # Model registry
        self.models = {
            "gpt-4": ChatOpenAI(model="gpt-4", temperature=0.7),
            "gpt-3.5-turbo": ChatOpenAI(model="gpt-3.5-turbo", temperature=0.7),
            "claude-3-opus": ChatAnthropic(model="claude-3-opus-20240229"),
            "claude-3-sonnet": ChatAnthropic(model="claude-3-sonnet-20240229")
        }

        # Checkpointer for state persistence
        self.checkpointer = SqliteSaver.from_conn_string(":memory:")

    def init_langsmith(self):
        """Initialize LangSmith for production observability"""
        api_key = os.getenv("LANGCHAIN_API_KEY")
        if api_key:
            self.langsmith_client = LangSmithClient(api_key=api_key)
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_PROJECT"] = self.project_name
            console.print("[green]✓ LangSmith observability enabled[/green]")
        else:
            console.print("[yellow]⚠ LangSmith not configured (set LANGCHAIN_API_KEY)[/yellow]")

    def add_stage_from_code(self, stage_def: StageDefinition):
        """Add a stage with executable code"""
        self.stages[stage_def.name] = stage_def
        console.print(f"[green]Added stage: {stage_def.name}[/green]")

    def create_stage_executor(self, stage_def: StageDefinition) -> Callable:
        """Create an executable function from stage definition"""

        async def execute_stage(state: PipelineState) -> PipelineState:
            stage_start = time.time()
            state["current_stage"] = stage_def.name

            # Create execution context
            execution_context = {
                "state": state,
                "models": self.models,
                "console": console,
                "trace_llm": self.trace_llm_call
            }

            # Compile and execute stage code
            try:
                # Create a namespace for the stage code
                namespace = execution_context.copy()

                # Execute the stage code
                exec(stage_def.code, namespace)

                # Call the main stage function if it exists
                if "process" in namespace:
                    result = await namespace["process"](state)
                    if isinstance(result, dict):
                        state["stage_outputs"][stage_def.name] = result

                # Record successful execution
                state["stages_completed"].append(stage_def.name)

                # Add to timeline
                state["execution_timeline"].append({
                    "stage": stage_def.name,
                    "start": stage_start,
                    "duration": time.time() - stage_start,
                    "status": "success"
                })

            except Exception as e:
                error_info = {
                    "stage": stage_def.name,
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                    "timestamp": datetime.now().isoformat()
                }
                state["errors"].append(error_info)
                console.print(f"[red]Error in {stage_def.name}: {str(e)}[/red]")

                # Add to timeline
                state["execution_timeline"].append({
                    "stage": stage_def.name,
                    "start": stage_start,
                    "duration": time.time() - stage_start,
                    "status": "error"
                })

            return state

        return execute_stage

    async def trace_llm_call(self,
                            model_name: str,
                            messages: List[Dict],
                            stage_name: str,
                            **kwargs) -> Dict:
        """Trace and execute an LLM call with full observability"""
        start_time = time.time()

        # Get model
        model = self.models.get(model_name)
        if not model:
            raise ValueError(f"Unknown model: {model_name}")

        # Convert messages
        langchain_messages = []
        for msg in messages:
            if msg["role"] == "system":
                langchain_messages.append(SystemMessage(content=msg["content"]))
            elif msg["role"] == "user":
                langchain_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                langchain_messages.append(AIMessage(content=msg["content"]))

        # Execute with tracing
        try:
            response = await model.ainvoke(langchain_messages, **kwargs)

            # Calculate metrics
            latency_ms = (time.time() - start_time) * 1000

            # Create trace
            trace = LLMTrace(
                id=f"{stage_name}_{int(time.time()*1000)}",
                stage=stage_name,
                timestamp=datetime.now(),
                model=model_name,
                provider="openai" if "gpt" in model_name else "anthropic",
                config=kwargs,
                messages=messages,
                response=response.content,
                usage=getattr(response, 'response_metadata', {}).get('token_usage', {}),
                latency_ms=latency_ms,
                cost_usd=self.calculate_cost(model_name,
                                            getattr(response, 'response_metadata', {}))
            )

            self.llm_traces.append(trace)

            return {
                "content": response.content,
                "trace_id": trace.id,
                "metadata": response.response_metadata if hasattr(response, 'response_metadata') else {}
            }

        except Exception as e:
            trace = LLMTrace(
                id=f"{stage_name}_{int(time.time()*1000)}",
                stage=stage_name,
                timestamp=datetime.now(),
                model=model_name,
                provider="unknown",
                config=kwargs,
                messages=messages,
                response="",
                usage={},
                latency_ms=(time.time() - start_time) * 1000,
                cost_usd=0.0,
                error=str(e)
            )
            self.llm_traces.append(trace)
            raise

    def calculate_cost(self, model_name: str, metadata: Dict) -> float:
        """Calculate cost based on token usage"""
        # Simplified pricing (cents per 1K tokens)
        pricing = {
            "gpt-4": {"input": 0.03, "output": 0.06},
            "gpt-3.5-turbo": {"input": 0.001, "output": 0.002},
            "claude-3-opus": {"input": 0.015, "output": 0.075},
            "claude-3-sonnet": {"input": 0.003, "output": 0.015}
        }

        if model_name not in pricing:
            return 0.0

        token_usage = metadata.get("token_usage", {})
        input_tokens = token_usage.get("prompt_tokens", 0)
        output_tokens = token_usage.get("completion_tokens", 0)

        cost = (
            (input_tokens * pricing[model_name]["input"] / 1000) +
            (output_tokens * pricing[model_name]["output"] / 1000)
        )

        return round(cost, 6)

    def build_graph(self) -> StateGraph:
        """Build the LangGraph from defined stages"""
        self.graph = StateGraph(PipelineState)

        # Add nodes
        for name, stage_def in self.stages.items():
            executor = self.create_stage_executor(stage_def)
            self.graph.add_node(name, executor)

        # Add edges based on dependencies
        entry_points = []
        for name, stage_def in self.stages.items():
            if not stage_def.dependencies:
                entry_points.append(name)
            else:
                for dep in stage_def.dependencies:
                    if dep in self.stages:
                        self.graph.add_edge(dep, name)

        # Set entry point
        if entry_points:
            self.graph.set_entry_point(entry_points[0])

        # Connect final stages to END
        final_stages = []
        for name in self.stages:
            has_downstream = any(
                name in s.dependencies
                for s in self.stages.values()
            )
            if not has_downstream:
                final_stages.append(name)

        for stage in final_stages:
            self.graph.add_edge(stage, END)

        # Compile with checkpointer
        self.compiled_graph = self.graph.compile(checkpointer=self.checkpointer)

        return self.compiled_graph

    async def run_pipeline(self, initial_input: Dict) -> Dict:
        """Run the pipeline with full observability"""
        if not self.compiled_graph:
            self.build_graph()

        # Initialize state
        initial_state = {
            "current_stage": "",
            "stages_completed": [],
            "stage_outputs": {},
            "llm_traces": [],
            "execution_timeline": [],
            "errors": [],
            "metrics": {},
            "context": initial_input,
            "checkpoints": []
        }

        # Run with tracking
        console.print("[cyan]Starting pipeline execution...[/cyan]")

        async for event in self.compiled_graph.astream(initial_state):
            stage = event.get("current_stage", "unknown")
            console.print(f"[blue]Stage: {stage}[/blue]")

            # Store checkpoint
            checkpoint = {
                "timestamp": datetime.now().isoformat(),
                "stage": stage,
                "state_snapshot": json.dumps(event, default=str)
            }
            self.execution_history.append(checkpoint)

        console.print("[green]Pipeline execution completed![/green]")
        return event

    def generate_observability_report(self) -> str:
        """Generate comprehensive observability report"""
        report = []
        report.append("=" * 80)
        report.append(f"PIPELINE OBSERVABILITY REPORT - {self.project_name}")
        report.append("=" * 80)

        # LLM Calls Summary
        report.append("\n📊 LLM CALLS SUMMARY")
        report.append("-" * 40)

        if self.llm_traces:
            df = pd.DataFrame([
                {
                    "Stage": t.stage,
                    "Model": t.model,
                    "Latency (ms)": t.latency_ms,
                    "Tokens": sum(t.usage.values()),
                    "Cost ($)": t.cost_usd,
                    "Error": "Yes" if t.error else "No"
                }
                for t in self.llm_traces
            ])

            report.append(df.to_string())

            # Aggregate stats
            total_cost = sum(t.cost_usd for t in self.llm_traces)
            avg_latency = sum(t.latency_ms for t in self.llm_traces) / len(self.llm_traces)
            total_tokens = sum(sum(t.usage.values()) for t in self.llm_traces)

            report.append(f"\nTotal Cost: ${total_cost:.4f}")
            report.append(f"Average Latency: {avg_latency:.2f}ms")
            report.append(f"Total Tokens: {total_tokens}")

        # Stage Execution Timeline
        report.append("\n⏱️ EXECUTION TIMELINE")
        report.append("-" * 40)

        for event in self.execution_history[-10:]:  # Last 10 events
            report.append(f"{event['timestamp']}: {event['stage']}")

        return "\n".join(report)

    def export_traces_to_langsmith(self):
        """Export all traces to LangSmith for analysis"""
        if not self.langsmith_client:
            console.print("[yellow]LangSmith not configured[/yellow]")
            return

        for trace in self.llm_traces:
            # Create LangSmith run
            run = self.langsmith_client.create_run(
                name=f"{trace.stage}_llm_call",
                run_type="llm",
                inputs={"messages": trace.messages},
                outputs={"response": trace.response},
                extra={
                    "model": trace.model,
                    "config": trace.config,
                    "latency_ms": trace.latency_ms,
                    "cost_usd": trace.cost_usd
                }
            )

        console.print(f"[green]Exported {len(self.llm_traces)} traces to LangSmith[/green]")


def create_example_pipeline():
    """Create an example pipeline with multiple stages"""
    studio = EnhancedLangGraphStudio("ai_news_pipeline")

    # Stage 1: Research
    research_stage = StageDefinition(
        name="research",
        description="Research AI news from multiple sources",
        code="""
async def process(state):
    # Use the trace_llm function for observability
    response = await trace_llm(
        model_name="gpt-4",
        messages=[
            {"role": "system", "content": "You are an AI news researcher."},
            {"role": "user", "content": "Find the latest AI breakthroughs"}
        ],
        stage_name="research",
        temperature=0.7,
        max_tokens=2000
    )

    return {
        "research_results": response["content"],
        "sources": ["arxiv", "tech_blogs", "news_sites"]
    }
""",
        dependencies=[],
        llm_configs=[{
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 2000
        }],
        retry_config={"max_attempts": 3, "backoff": 2},
        timeout_seconds=60,
        validation_rules=["output must contain research_results"],
        test_cases=[]
    )

    # Stage 2: Script Writing
    script_stage = StageDefinition(
        name="script_writing",
        description="Write engaging script from research",
        code="""
async def process(state):
    research = state["stage_outputs"].get("research", {}).get("research_results", "")

    response = await trace_llm(
        model_name="claude-3-opus",
        messages=[
            {"role": "system", "content": "You are a video script writer."},
            {"role": "user", "content": f"Write a script based on: {research}"}
        ],
        stage_name="script_writing",
        temperature=0.8,
        max_tokens=3000
    )

    return {
        "script": response["content"],
        "duration_estimate": 120  # seconds
    }
""",
        dependencies=["research"],
        llm_configs=[{
            "model": "claude-3-opus",
            "temperature": 0.8,
            "max_tokens": 3000
        }],
        retry_config={"max_attempts": 2},
        timeout_seconds=90,
        validation_rules=["output must contain script"],
        test_cases=[]
    )

    studio.add_stage_from_code(research_stage)
    studio.add_stage_from_code(script_stage)

    return studio


if __name__ == "__main__":
    # Create example pipeline
    studio = create_example_pipeline()

    # Build and visualize
    studio.build_graph()

    # Run pipeline
    asyncio.run(studio.run_pipeline({"topic": "AI breakthroughs"}))

    # Generate report
    report = studio.generate_observability_report()
    console.print(report)

    # Export to LangSmith
    studio.export_traces_to_langsmith()