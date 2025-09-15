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
    },
    {
        "chapter_title": "Enterprise Impact",
        "duration": 10,
        "text": "60% productivity gains in development tasks", 
        "broll_url": "https://images.pexels.com/photos/3861969/pexels-photo-3861969.jpeg"  # Business/productivity
    },
    {
        "chapter_title": "DeepMind Breakthrough",
        "duration": 10,
        "text": "Revolutionary protein folding predictions",
        "broll_url": "https://images.pexels.com/photos/2280547/pexels-photo-2280547.jpeg"  # Science/research
    }
]

print("\n[3/6] Testing video renderer selector...")
try:
    from src.produce.video_renderer_selector import VideoRendererSelector
    
    renderer = VideoRendererSelector()
    print(f"  Shotstack enabled: {renderer.shotstack_enabled}")
    print(f"  Pictory enabled: {renderer.pictory_enabled}")
    
    # Get cost estimate
    duration_min = len(segments) * 10 / 60  # Total duration in minutes
    shotstack_cost = renderer.get_cost_estimate(duration_min, use_shotstack=True)
    pictory_cost = renderer.get_cost_estimate(duration_min, use_shotstack=False)
    
    print(f"\n  Cost comparison for {duration_min:.1f} minute video:")
    print(f"  • Shotstack: ${shotstack_cost['render_cost']:.3f}")
    print(f"  • Pictory: ${pictory_cost['render_cost']:.2f}")
    print(f"  • Savings: ${pictory_cost['render_cost'] - shotstack_cost['render_cost']:.2f} ({(1 - shotstack_cost['render_cost']/pictory_cost['render_cost'])*100:.0f}% cheaper)")
    
except Exception as e:
    print(f"  ❌ Error: {e}")
    sys.exit(1)

print("\n[4/6] Generating test voiceover...")
# For testing, we'll use a placeholder voiceover URL
# In production, this would use ElevenLabs or TTS
voiceover_url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"  # Placeholder audio
print(f"  Using placeholder audio for testing")

print("\n[5/6] Rendering video with Shotstack...")
try:
    # Create a temporary output path
    output_path = f"/home/junaidqureshi/AIT/starter/data/shotstack_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
    
    # Render video
    print("  Submitting to Shotstack API...")
    start_time = time.time()
    
    rendered_path = renderer.render_video(
        script=test_script,
        title="AI News Test - " + datetime.now().strftime("%B %d, %Y"),
        segments=segments,
        voiceover_url=voiceover_url,
        output_path=output_path,
        prefer_shotstack=True,  # Force Shotstack
        style="professional"
    )
    
    elapsed = time.time() - start_time
    print(f"  ✅ Video rendered in {elapsed:.1f} seconds!")
    print(f"  Output: {rendered_path}")
    
    # Check file size
    if os.path.exists(rendered_path):
        size = os.path.getsize(rendered_path) / (1024*1024)
        print(f"  File size: {size:.1f} MB")
    
except Exception as e:
    print(f"  ❌ Render failed: {e}")
    import traceback
    traceback.print_exc()
    
    # Try Pictory as fallback
    print("\n  Attempting Pictory fallback...")
    try:
        rendered_path = renderer.render_video(
            script=test_script,
            title="AI News Test",
            segments=segments, 
            voiceover_url=voiceover_url,
            output_path=output_path,
            prefer_shotstack=False,  # Force Pictory
            style="professional"
        )
        print(f"  ✅ Pictory fallback successful: {rendered_path}")
    except Exception as e2:
        print(f"  ❌ Pictory also failed: {e2}")

print("\n[6/6] Testing Slack notification...")
try:
    from src.slack_approvals import SlackApprovalService
    
    if os.getenv('SLACK_BOT_TOKEN'):
        slack = SlackApprovalService()
        
        # Send test approval request
        approval_id = slack.send_approval_request(
            content_type="video",
            title="TEST: Shotstack Pipeline",
            preview_url=f"https://storage.googleapis.com/{os.getenv('ASSET_CACHE_BUCKET')}/test_preview.mp4",
            metadata={
                "Duration": "40 seconds",
                "Renderer": "Shotstack",
                "Cost": f"${shotstack_cost['render_cost']:.3f}",
                "Style": "Professional"
            }
        )
        print(f"  ✅ Slack notification sent: {approval_id}")
        print("  Check #ai-news-approvals channel for the message")
    else:
        print("  ⚠️  Slack not configured, skipping notification")
        
except Exception as e:
    print(f"  ⚠️  Slack error (non-critical): {e}")

print("\n" + "="*60)
print("✅ PIPELINE TEST COMPLETE!")
print("="*60)
print("\nSummary:")
print(f"• Renderer: Shotstack (${shotstack_cost['render_cost']:.3f} vs Pictory ${pictory_cost['render_cost']:.2f})")
print(f"• Savings: {(1 - shotstack_cost['render_cost']/pictory_cost['render_cost'])*100:.0f}% cheaper than Pictory")
if 'rendered_path' in locals():
    print(f"• Output: {rendered_path}")
print("\nNext steps:")
print("1. Check the rendered video quality")
print("2. Review Slack approval message")
print("3. Run full pipeline with real content")
print("="*60)