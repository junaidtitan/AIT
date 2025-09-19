#!/bin/bash
cd ~/AIT
export PATH=$HOME/.local/bin:$PATH
export LANGCHAIN_API_KEY=$(gcloud secrets versions access latest --secret=LANGSMITH_API_KEY 2>/dev/null || gcloud secrets versions access latest --secret=LANGCHAIN_API_KEY)
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_PROJECT='aitube-pipeline'
export LANGCHAIN_ENDPOINT='https://api.smith.langchain.com'
export OPENAI_API_KEY=$(gcloud secrets versions access latest --secret=OPENAI_API_KEY)
export ELEVENLABS_API_KEY=$(gcloud secrets versions access latest --secret=ELEVENLABS_API_KEY)
export SHOTSTACK_API_KEY=$(gcloud secrets versions access latest --secret=SHOTSTACK_API_KEY)
export PYTHONPATH=$(pwd)

echo 'Starting LangGraph Studio...'
~/.local/bin/langgraph dev --port 8000 --host 0.0.0.0
