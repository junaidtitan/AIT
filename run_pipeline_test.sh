#!/bin/bash
set -e

echo "Loading secrets..."
source scripts/load_secrets.sh

echo "Setting environment..."
export ELEVENLABS_VOICE_ID=ygkaO6a4xYPwmJY5LCz9
export USE_SHEETS_SOURCES=false
export PYTHONUNBUFFERED=1

echo "Running pipeline with sample script..."
timeout 20 python3 unified_pipeline_test.py --sample-script --output-dir test_output 2>&1 | tee pipeline_test.log | head -100

echo ""
echo "Pipeline test completed or timed out after 20 seconds"
echo "Check pipeline_test.log for full output"