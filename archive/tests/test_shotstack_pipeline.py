#!/usr/bin/env python3
"""
Test the enhanced pipeline with Shotstack rendering
"""
import os
import sys
import subprocess
import time
from datetime import datetime

print("="*60)
print("🚀 TESTING ENHANCED PIPELINE WITH SHOTSTACK")
print("="*60)

# Load credentials from GCP Secret Manager
print("\n[1/6] Loading credentials...")
secrets = ['SHOTSTACK_API_KEY', 'PICTORY_CLIENT_ID', 'PICTORY_CLIENT_SECRET', 
           'PEXELS_API_KEY', 'SLACK_BOT_TOKEN']

for secret in secrets:
    try:
        value = subprocess.check_output(
            ['gcloud', 'secrets', 'versions', 'access', 'latest', f'--secret={secret}'],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        os.environ[secret] = value
        print(f"  ✅ {secret} loaded")
    except:
        print(f"  ⚠️  {secret} not found")

os.environ['ASSET_CACHE_BUCKET'] = 'yta-main-assets'

# Add path
sys.path.insert(0, '/home/junaidqureshi/AIT')

# Test script - short for quick testing
test_script = """
Breaking AI News: OpenAI has announced GPT-5, marking a revolutionary leap in artificial intelligence.
The new model demonstrates 40% improved accuracy and dramatically reduced hallucination rates.
Enterprise clients report unprecedented productivity gains, with some seeing 60% improvement in development tasks.
Meanwhile, Google DeepMind achieves a breakthrough in protein folding that could revolutionize drug discovery.
"""

print("\n[2/6] Preparing test content...")
print(f"  Script: {len(test_script.split())} words")
print(f"  Est. duration: ~{len(test_script.split())/150*60:.0f} seconds")

# Create test segments for B-roll
segments = [
    {
        "chapter_title": "GPT-5 Announcement",
        "duration": 10,
        "text": "OpenAI announces GPT-5 with breakthrough capabilities",
        "broll_url": "https://images.pexels.com/photos/373543/pexels-photo-373543.jpeg"  # AI/tech image
    },
    {
        "chapter_title": "Performance Gains", 
        "duration": 10,
        "text": "40% improved accuracy with reduced hallucinations",
        "broll_url": "https://images.pexels.com/photos/590022/pexels-photo-590022.jpeg"  # Data visualization
    }
]

