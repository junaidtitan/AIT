#!/usr/bin/env python3
"""
Hybrid Approach: Use Langflow UI with direct LangGraph code access
Best of both worlds - visual editing AND programmatic control
"""

from langflow import load_flow_from_json
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnablePassthrough
import json


class HybridPipelineManager:
    """Use Langflow for visual design, LangGraph for execution"""

    def __init__(self):
        self.langflow_flow = None
        self.langgraph_graph = None

    def import_from_langflow(self, flow_path: str):
        """Import a flow designed in Langflow UI"""
        with open(flow_path, 'r') as f:
            flow_config = json.load(f)

        # Convert Langflow flow to LangGraph
        self.langgraph_graph = self.convert_to_langgraph(flow_config)
        return self.langgraph_graph

    def convert_to_langgraph(self, flow_config: dict) -> StateGraph:
        """Convert Langflow visual flow to executable LangGraph"""
        graph = StateGraph(dict)

        # Add nodes from Langflow
        for node in flow_config.get("nodes", []):
            # Each Langflow node becomes a LangGraph node
            graph.add_node(
                node["id"],
                self.create_node_function(node)
            )

        # Add edges from Langflow connections
        for edge in flow_config.get("edges", []):
            graph.add_edge(edge["source"], edge["target"])

        # Set entry point
        if flow_config.get("nodes"):
            graph.set_entry_point(flow_config["nodes"][0]["id"])

        return graph.compile()

    def create_node_function(self, node_config: dict):
        """Create executable function from Langflow node config"""
        def node_function(state):
            # This executes the actual logic
            # You can access the visual config here
            print(f"Executing {node_config['id']} with config: {node_config['data']}")

            # Your actual stage logic
            if node_config["type"] == "AITResearchStage":
                # Call your existing research code
                from src.ingest.rss_arxiv import fetch_rss
                results = fetch_rss()
                state["research_results"] = results

            elif node_config["type"] == "AITScriptWriterStage":
                # Call your existing script writer
                from src.editorial.script_writer import generate_script
                script = generate_script(state.get("research_results"))
                state["script"] = script

            return state

        return node_function

    def export_to_langflow(self, graph: StateGraph, output_path: str):
        """Export LangGraph to Langflow format for visual editing"""
        flow_config = {
            "nodes": [],
            "edges": []
        }

        # Convert LangGraph nodes to Langflow format
        for node_name, node_func in graph.nodes.items():
            flow_config["nodes"].append({
                "id": node_name,
                "type": "CustomComponent",
                "position": {"x": 100, "y": 100},
                "data": {}
            })

        # Convert edges
        for edge in graph.edges:
            flow_config["edges"].append({
                "source": edge[0],
                "target": edge[1]
            })

        with open(output_path, 'w') as f:
            json.dump(flow_config, f, indent=2)

        return flow_config


# Example: Use both together
if __name__ == "__main__":
    manager = HybridPipelineManager()

    # Option 1: Design in Langflow UI, execute with LangGraph
    langgraph = manager.import_from_langflow("flows/ait_pipeline_flow.json")

    # Option 2: Build in code, visualize in Langflow
    graph = StateGraph(dict)
    graph.add_node("research", lambda x: x)
    graph.add_node("script", lambda x: x)
    graph.add_edge("research", "script")
    graph.set_entry_point("research")

    manager.export_to_langflow(graph, "flows/exported_flow.json")

    print("✅ You can now:")
    print("1. Design visually in Langflow UI (http://localhost:7860)")
    print("2. Execute with LangGraph programmatically")
    print("3. Switch between visual and code seamlessly")