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
timestamp = datetime.now().strftime("%H%M%S")
output_path = f"/home/junaidqureshi/AIT/starter/data/shotstack_{timestamp}.mp4"

try:
    start = time.time()
    result = api.render_news_video(
        title="AI News Brief",
        segments=segments,
        voiceover_url=voiceover_url,
        duration=20,
        output_path=output_path,
        style="professional"
    )
    elapsed = time.time() - start
    
    # Check file
    if os.path.exists(output_path):
        size = os.path.getsize(output_path) / (1024*1024)
        print(f"\n✅ SUCCESS!")
        print(f"  • Time: {elapsed:.1f} seconds")
        print(f"  • File: {output_path}")
        print(f"  • Size: {size:.1f} MB")
        print(f"  • Cost: ~$0.002 (vs Pictory $0.50)")
        
        # Send Slack notification if configured
        if os.getenv("SLACK_BOT_TOKEN"):
            print("\n[3/3] Sending Slack notification...")
            slack = SlackApprovalService()
            approval_id = slack.send_approval_request(
                content_type="video",
                title="TEST: Shotstack Video",
                preview_url=f"file://{output_path}",
                metadata={
                    "Duration": "20 seconds",
                    "Renderer": "Shotstack",
                    "Cost": "$0.002",
                    "Time": f"{elapsed:.1f}s"
                }
            )
            print(f"  ✅ Slack approval sent: {approval_id}")
            
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("TEST COMPLETE")
print("="*60)
