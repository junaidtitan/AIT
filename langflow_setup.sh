#!/bin/bash

# Langflow Setup Script with Custom Components
set -e

echo "🚀 Setting up Langflow for Visual Pipeline Development"

# Install Langflow locally (alternative to Docker)
echo "📦 Installing Langflow..."
pip install langflow>=1.0.0 langfuse langsmith

# Create directories for flows and components
mkdir -p flows custom_components langflow_data

# Create custom component for your pipeline stages
cat > custom_components/ait_pipeline_stages.py << 'EOF'
from langflow.custom import CustomComponent
from langflow.field_typing import Data
from typing import Optional, Dict, Any
import asyncio
from datetime import datetime

class AITResearchStage(CustomComponent):
    display_name = "AIT Research Stage"
    description = "Research AI news from multiple sources"

    def build_config(self) -> dict:
        return {
            "sources": {
                "display_name": "News Sources",
                "options": ["arxiv", "tech_blogs", "news_sites", "reddit", "twitter"],
                "value": ["arxiv", "tech_blogs"],
                "multiselect": True,
            },
            "model": {
                "display_name": "LLM Model",
                "options": ["gpt-4", "gpt-3.5-turbo", "claude-3-opus"],
                "value": "gpt-4",
            },
            "temperature": {
                "display_name": "Temperature",
                "field_type": "float",
                "value": 0.7,
                "range": [0, 2],
            },
            "max_tokens": {
                "display_name": "Max Tokens",
                "field_type": "int",
                "value": 2000,
            }
        }

    async def build(
        self,
        sources: list,
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> Data:
        # Your existing research logic here
        from src.ingest.rss_arxiv import fetch_rss

        results = []
        for source in sources:
            # Fetch from each source
            pass

        return Data(
            value={
                "research_results": results,
                "timestamp": datetime.now().isoformat(),
                "model_config": {
                    "model": model,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
            }
        )


class AITScriptWriterStage(CustomComponent):
    display_name = "AIT Script Writer"
    description = "Generate video script from research"

    def build_config(self) -> dict:
        return {
            "style": {
                "display_name": "Script Style",
                "options": ["educational", "entertaining", "news", "documentary"],
                "value": "educational",
            },
            "duration": {
                "display_name": "Target Duration (seconds)",
                "field_type": "int",
                "value": 120,
            },
            "model": {
                "display_name": "LLM Model",
                "options": ["gpt-4", "claude-3-opus", "claude-3-sonnet"],
                "value": "claude-3-opus",
            },
            "include_hooks": {
                "display_name": "Include Hooks",
                "field_type": "bool",
                "value": True,
            }
        }

    async def build(
        self,
        research_data: Data,
        style: str,
        duration: int,
        model: str,
        include_hooks: bool,
    ) -> Data:
        # Your script generation logic
        from src.editorial.script_writer import ScriptWriter

        script = f"Generated script based on research..."

        return Data(
            value={
                "script": script,
                "duration": duration,
                "style": style,
                "model_used": model
            }
        )
EOF

# Create example flow configuration
cat > flows/ait_pipeline_flow.json << 'EOF'
{
  "name": "AIT Video Pipeline",
  "description": "Complete AI news video generation pipeline",
  "nodes": [
    {
      "id": "research",
      "type": "AITResearchStage",
      "position": {"x": 100, "y": 100},
      "data": {
        "sources": ["arxiv", "tech_blogs"],
        "model": "gpt-4",
        "temperature": 0.7
      }
    },
    {
      "id": "script",
      "type": "AITScriptWriterStage",
      "position": {"x": 400, "y": 100},
      "data": {
        "style": "educational",
        "duration": 120,
        "model": "claude-3-opus"
      }
    }
  ],
  "edges": [
    {
      "source": "research",
      "target": "script",
      "sourceHandle": "research_results",
      "targetHandle": "research_data"
    }
  ]
}
EOF

# Create configuration file
cat > .langflow.env << 'EOF'
# Langflow Configuration
LANGFLOW_HOST=0.0.0.0
LANGFLOW_PORT=7860
LANGFLOW_WORKERS=1
LANGFLOW_LOG_LEVEL=info
LANGFLOW_DATABASE_URL=sqlite:///./langflow_data/langflow.db

# LangSmith Integration (for observability)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=ait-pipeline
LANGCHAIN_ENDPOINT=https://api.smith.langchain.com

# Model Providers
OPENAI_API_KEY=${OPENAI_API_KEY}
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
PERPLEXITY_API_KEY=${PERPLEXITY_API_KEY}

# Custom Component Path
LANGFLOW_COMPONENTS_PATH=./custom_components

# Cache Settings
LANGFLOW_CACHE_TYPE=redis
REDIS_URL=redis://localhost:6379

# Security
LANGFLOW_AUTO_LOGIN=false
LANGFLOW_SUPERUSER=admin
EOF

echo "✅ Langflow setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Set your API keys in .langflow.env"
echo "2. Run: langflow run --env-file .langflow.env"
echo "3. Open browser at http://localhost:7860"
echo "4. Import the flow from flows/ait_pipeline_flow.json"
echo ""
echo "🎨 Features available:"
echo "- Visual drag-and-drop pipeline builder"
echo "- Real-time code editing per node"
echo "- LLM config visibility and editing"
echo "- LangSmith integration for observability"
echo "- Custom components for your specific stages"