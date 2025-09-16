#!/usr/bin/env python3
"""Quick test of Shotstack rendering"""
import os, sys, subprocess, time
from datetime import datetime

print("="*60)
print("🚀 TESTING SHOTSTACK VIDEO GENERATION")
print("="*60)

# Load credentials
sys.path.insert(0, "/home/junaidqureshi/AIT")
os.environ["ASSET_CACHE_BUCKET"] = "yta-main-assets"

for secret in ["SHOTSTACK_API_KEY", "SLACK_BOT_TOKEN"]:
    try:
        value = subprocess.check_output(
            ["gcloud", "secrets", "versions", "access", "latest", f"--secret={secret}"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        os.environ[secret] = value
        print(f"  ✅ {secret} loaded")
    except:
        print(f"  ⚠️  {secret} not found")

# Test script - very short for quick testing
test_script = """
Breaking news: OpenAI announces GPT-5 with revolutionary capabilities.
The model shows 40% improved accuracy and reduced hallucinations.
Early tests indicate unprecedented performance gains.
"""

print(f"\nScript: {len(test_script.split())} words (~20 seconds)")

# Import after setting env vars
from src.produce.shotstack_enhanced import ShotstackEnhanced
from src.slack_approvals import SlackApprovalService

# Test segments
segments = [
    {
        "chapter_title": "GPT-5 Breakthrough",
        "duration": 10,
        "text": "Revolutionary AI model announced",
        "broll_url": "https://images.pexels.com/photos/373543/pexels-photo-373543.jpeg"
    },
    {
        "chapter_title": "Performance Gains",
        "duration": 10,
        "text": "40% accuracy improvement demonstrated",
        "broll_url": "https://images.pexels.com/photos/590022/pexels-photo-590022.jpeg"
    }
]

print("\n[1/3] Initializing Shotstack...")
api = ShotstackEnhanced()

# Simple voiceover placeholder (in production would use TTS)
voiceover_url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3"

print("[2/3] Rendering video with Shotstack...")

