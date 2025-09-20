#!/usr/bin/env python3
"""
Visual Pipeline Studio - Interactive LangGraph Development Environment
Provides visual code editing, flow management, and LLM observability
"""

import os
import sys
import json
import asyncio
from typing import Dict, List, Any, Optional, TypedDict
from datetime import datetime
from pathlib import Path
import streamlit as st
import graphviz
from dataclasses import dataclass, asdict
import yaml

from langchain_core.messages import HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langsmith import Client as LangSmithClient
from langsmith.run_trees import RunTree

@dataclass
class StageConfig:
    """Configuration for a pipeline stage"""
    name: str
    description: str
    code: str
    llm_config: Dict[str, Any]
    inputs: List[str]
    outputs: List[str]
    retry_policy: Dict[str, Any] = None
    timeout: int = 300

@dataclass
class LLMCall:
    """Record of an LLM call with full config"""
    stage: str
    timestamp: datetime
    model: str
    temperature: float
    max_tokens: int
    prompt: str
    response: str
    latency: float
    tokens_used: Dict[str, int]
    cost: float

class PipelineState(TypedDict):
    """Shared state for the pipeline"""
    current_stage: str
    stages_completed: List[str]
    artifacts: Dict[str, Any]
    llm_calls: List[Dict]
    errors: List[str]
    metadata: Dict[str, Any]

class VisualPipelineStudio:
    """Interactive visual development environment for LangGraph pipelines"""

    def __init__(self):
        self.stages: Dict[str, StageConfig] = {}
        self.graph: Optional[StateGraph] = None
        self.llm_calls: List[LLMCall] = []
        self.langsmith_client = None
        self.init_observability()

    def init_observability(self):
        """Initialize LangSmith for observability"""
        if os.getenv("LANGCHAIN_API_KEY"):
            self.langsmith_client = LangSmithClient()
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_PROJECT"] = "visual-pipeline-studio"

    def add_stage(self, config: StageConfig):
        """Add a stage to the pipeline"""
        self.stages[config.name] = config

    def visualize_flow(self) -> str:
        """Generate GraphViz visualization of the pipeline flow"""
        dot = graphviz.Digraph(comment='Pipeline Flow')
        dot.attr(rankdir='TB')

        # Add nodes for each stage
        for name, stage in self.stages.items():
            label = f"{name}\\n{stage.description[:30]}..."
            dot.node(name, label, shape='box', style='rounded,filled',
                    fillcolor='lightblue')

        # Add edges based on inputs/outputs
        for name, stage in self.stages.items():
            for output in stage.outputs:
                for other_name, other_stage in self.stages.items():
                    if output in other_stage.inputs and name != other_name:
                        dot.edge(name, other_name, label=output)

        dot.node('END', 'END', shape='doublecircle', style='filled',
                fillcolor='lightgreen')

        return dot.source

    def create_stage_function(self, stage_config: StageConfig):
        """Create a function for a stage with LLM tracking"""
        async def stage_function(state: PipelineState) -> PipelineState:
            start_time = datetime.now()
            state["current_stage"] = stage_config.name

            # Initialize LLM with config
            llm = ChatOpenAI(
                model=stage_config.llm_config.get("model", "gpt-4"),
                temperature=stage_config.llm_config.get("temperature", 0.7),
                max_tokens=stage_config.llm_config.get("max_tokens", 2000)
            )

            # Execute stage code (simplified - in production would use exec or import)
            try:
                # Track LLM call
                prompt = stage_config.llm_config.get("prompt_template", "").format(
                    **state["artifacts"]
                )

                response = await llm.ainvoke([HumanMessage(content=prompt)])

                # Record LLM call details
                llm_call = LLMCall(
                    stage=stage_config.name,
                    timestamp=datetime.now(),
                    model=stage_config.llm_config.get("model"),
                    temperature=stage_config.llm_config.get("temperature"),
                    max_tokens=stage_config.llm_config.get("max_tokens"),
                    prompt=prompt,
                    response=response.content,
                    latency=(datetime.now() - start_time).total_seconds(),
                    tokens_used={"prompt": len(prompt.split()),
                                "completion": len(response.content.split())},
                    cost=0.0  # Calculate based on model pricing
                )

                state["llm_calls"].append(asdict(llm_call))
                self.llm_calls.append(llm_call)

                # Update artifacts
                for output in stage_config.outputs:
                    state["artifacts"][output] = response.content

                state["stages_completed"].append(stage_config.name)

            except Exception as e:
                state["errors"].append(f"{stage_config.name}: {str(e)}")

            return state

        return stage_function

    def build_graph(self):
        """Build the LangGraph from configured stages"""
        self.graph = StateGraph(PipelineState)

        # Add nodes for each stage
        for name, stage in self.stages.items():
            self.graph.add_node(name, self.create_stage_function(stage))

        # Add edges based on dependencies
        stage_names = list(self.stages.keys())
        if stage_names:
            self.graph.set_entry_point(stage_names[0])

            for i in range(len(stage_names) - 1):
                self.graph.add_edge(stage_names[i], stage_names[i + 1])

            self.graph.add_edge(stage_names[-1], END)

        return self.graph.compile()

    def export_config(self, filepath: str):
        """Export pipeline configuration to YAML"""
        config = {
            "pipeline": {
                "name": "Visual Pipeline",
                "stages": {}
            }
        }

        for name, stage in self.stages.items():
            config["pipeline"]["stages"][name] = asdict(stage)

        with open(filepath, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)

    def import_config(self, filepath: str):
        """Import pipeline configuration from YAML"""
        with open(filepath, 'r') as f:
            config = yaml.load(f, Loader=yaml.SafeLoader)

        for name, stage_dict in config["pipeline"]["stages"].items():
            self.stages[name] = StageConfig(**stage_dict)


def create_streamlit_ui():
    """Create Streamlit UI for visual pipeline development"""
    st.set_page_config(page_title="Visual Pipeline Studio", layout="wide")

    # Initialize session state
    if 'studio' not in st.session_state:
        st.session_state.studio = VisualPipelineStudio()

    studio = st.session_state.studio

    st.title("🎨 Visual Pipeline Studio")
    st.markdown("Interactive LangGraph Development with Visual Code Editing")

    # Sidebar for stage management
    with st.sidebar:
        st.header("Pipeline Stages")

        # Add new stage
        with st.expander("➕ Add New Stage"):
            stage_name = st.text_input("Stage Name")
            stage_desc = st.text_area("Description")

            st.subheader("LLM Configuration")
            model = st.selectbox("Model", ["gpt-4", "gpt-3.5-turbo", "claude-3"])
            temperature = st.slider("Temperature", 0.0, 2.0, 0.7)
            max_tokens = st.number_input("Max Tokens", 100, 8000, 2000)

            inputs = st.text_input("Inputs (comma-separated)")
            outputs = st.text_input("Outputs (comma-separated)")

            if st.button("Add Stage"):
                config = StageConfig(
                    name=stage_name,
                    description=stage_desc,
                    code="",  # Will be edited in main panel
                    llm_config={
                        "model": model,
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    },
                    inputs=inputs.split(",") if inputs else [],
                    outputs=outputs.split(",") if outputs else []
                )
                studio.add_stage(config)
                st.rerun()

        # List existing stages
        st.subheader("Current Stages")
        for name in studio.stages:
            if st.button(f"📝 {name}"):
                st.session_state.selected_stage = name

    # Main content area
    col1, col2 = st.columns([2, 1])

    with col1:
        st.header("Stage Editor")

        if 'selected_stage' in st.session_state:
            stage = studio.stages[st.session_state.selected_stage]

            # Code editor
            st.subheader(f"Editing: {stage.name}")

            # Show current LLM config
            with st.expander("🤖 LLM Configuration"):
                st.json(stage.llm_config)

            # Code editing area
            new_code = st.text_area(
                "Stage Code",
                value=stage.code,
                height=400,
                key=f"code_{stage.name}"
            )

            # Prompt template editor
            prompt_template = st.text_area(
                "Prompt Template",
                value=stage.llm_config.get("prompt_template", ""),
                height=200,
                help="Use {variable} for template variables"
            )

            if st.button("💾 Save Changes"):
                stage.code = new_code
                stage.llm_config["prompt_template"] = prompt_template
                st.success(f"Saved changes to {stage.name}")
        else:
            st.info("Select a stage from the sidebar to edit")

    with col2:
        st.header("Pipeline Flow")

        # Visualize the flow
        if studio.stages:
            flow_viz = studio.visualize_flow()
            st.graphviz_chart(flow_viz)
        else:
            st.info("Add stages to see the flow")

    # LLM Calls Observatory
    st.header("🔍 LLM Calls Observatory")

    if studio.llm_calls:
        # Create tabs for different views
        tab1, tab2, tab3 = st.tabs(["Recent Calls", "Analytics", "Config Details"])

        with tab1:
            for call in studio.llm_calls[-5:]:  # Show last 5 calls
                with st.expander(f"{call.stage} - {call.timestamp.strftime('%H:%M:%S')}"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Model", call.model)
                        st.metric("Temperature", call.temperature)
                    with col2:
                        st.metric("Latency", f"{call.latency:.2f}s")
                        st.metric("Max Tokens", call.max_tokens)
                    with col3:
                        st.metric("Tokens Used", sum(call.tokens_used.values()))
                        st.metric("Cost", f"${call.cost:.4f}")

                    st.text_area("Prompt", call.prompt, height=100)
                    st.text_area("Response", call.response, height=100)

        with tab2:
            # Analytics dashboard
            st.subheader("Performance Metrics")
            avg_latency = sum(c.latency for c in studio.llm_calls) / len(studio.llm_calls)
            total_tokens = sum(sum(c.tokens_used.values()) for c in studio.llm_calls)
            total_cost = sum(c.cost for c in studio.llm_calls)

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Avg Latency", f"{avg_latency:.2f}s")
            with col2:
                st.metric("Total Tokens", total_tokens)
            with col3:
                st.metric("Total Cost", f"${total_cost:.2f}")

        with tab3:
            # Configuration comparison
            st.subheader("Stage Configurations")
            config_data = []
            for name, stage in studio.stages.items():
                config_data.append({
                    "Stage": name,
                    "Model": stage.llm_config.get("model"),
                    "Temperature": stage.llm_config.get("temperature"),
                    "Max Tokens": stage.llm_config.get("max_tokens")
                })
            st.table(config_data)

    # Control panel
    st.header("🎮 Control Panel")
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("▶️ Run Pipeline"):
            compiled_graph = studio.build_graph()
            st.info("Pipeline running...")
            # Run logic here

    with col2:
        if st.button("📊 View Traces"):
            if studio.langsmith_client:
                st.info("Opening LangSmith traces...")
                st.write("https://smith.langchain.com")

    with col3:
        if st.button("💾 Export Config"):
            studio.export_config("pipeline_config.yaml")
            st.success("Exported to pipeline_config.yaml")

    with col4:
        uploaded_file = st.file_uploader("Import Config", type="yaml")
        if uploaded_file:
            # Save uploaded file temporarily and import
            with open("temp_config.yaml", "wb") as f:
                f.write(uploaded_file.getbuffer())
            studio.import_config("temp_config.yaml")
            st.success("Configuration imported!")
            st.rerun()


if __name__ == "__main__":
    # Check if running in Streamlit mode
    if len(sys.argv) > 1 and sys.argv[1] == "ui":
        create_streamlit_ui()
    else:
        # CLI mode for testing
        print("Visual Pipeline Studio")
        print("Run with 'streamlit run visual_pipeline_studio.py ui' for UI")

        # Example usage
        studio = VisualPipelineStudio()

        # Add sample stages
        stage1 = StageConfig(
            name="research",
            description="Research AI news",
            code="# Research logic here",
            llm_config={
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 2000,
                "prompt_template": "Research the following topic: {topic}"
            },
            inputs=["topic"],
            outputs=["research_results"]
        )

        stage2 = StageConfig(
            name="script_writing",
            description="Write video script",
            code="# Script writing logic",
            llm_config={
                "model": "gpt-4",
                "temperature": 0.8,
                "max_tokens": 3000,
                "prompt_template": "Write a script based on: {research_results}"
            },
            inputs=["research_results"],
            outputs=["script"]
        )

        studio.add_stage(stage1)
        studio.add_stage(stage2)

        # Export configuration
        studio.export_config("example_pipeline.yaml")
        print("Example pipeline configuration exported to example_pipeline.yaml")