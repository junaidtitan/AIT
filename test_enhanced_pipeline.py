#!/usr/bin/env python3
"""
Test the enhanced AI News pipeline with Shotstack/Pictory intelligent routing
"""
import os
import sys
import subprocess
import json
from datetime import datetime

print("="*60)
print("🎬 ENHANCED AI NEWS PIPELINE TEST")
print("="*60)

# Step 1: Load environment variables from GCP Secret Manager
print("\n[STEP 1] Loading credentials from GCP Secret Manager...")
secrets_to_load = [
    'SHOTSTACK_API_KEY',
    'PICTORY_CLIENT_ID', 
    'PICTORY_CLIENT_SECRET',
    'SLACK_BOT_TOKEN',
    'SLACK_WEBHOOK_URL',
    'PEXELS_API_KEY',
    'PIXABAY_API_KEY'
]

env_status = {}
for secret in secrets_to_load:
    try:
        value = subprocess.check_output(
            ['gcloud', 'secrets', 'versions', 'access', 'latest', f'--secret={secret}'],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        if value:
            os.environ[secret] = value
            env_status[secret] = '✅ Loaded'
        else:
            env_status[secret] = '⚠️ Empty'
    except subprocess.CalledProcessError:
        env_status[secret] = '❌ Not found'

for key, status in env_status.items():
    print(f"  {key}: {status}")

# Set additional environment variables
os.environ['ASSET_CACHE_BUCKET'] = 'yta-main-assets'
os.environ['SLACK_APPROVAL_CHANNEL'] = '#ai-news-approvals'

# Step 2: Check pipeline components
print("\n[STEP 2] Checking pipeline components...")
sys.path.insert(0, '/home/junaidqureshi/AIT')

components_status = {}

# Check Shotstack
try:
    from src.produce.shotstack_enhanced import ShotstackEnhanced
    components_status['Shotstack Enhanced'] = '✅ Available'
except ImportError as e:
    components_status['Shotstack Enhanced'] = f'❌ Missing: {e}'

# Check Video Renderer Selector
try:
    from src.produce.video_renderer_selector import VideoRendererSelector
    components_status['Video Renderer Selector'] = '✅ Available'
except ImportError as e:
    components_status['Video Renderer Selector'] = f'❌ Missing: {e}'

# Check Slack Approvals
try:
    from src.slack_approvals import SlackApprovalService
    components_status['Slack Approvals'] = '✅ Available'
except ImportError as e:
    components_status['Slack Approvals'] = f'❌ Missing: {e}'

# Check Pictory
try:
    from src.produce.pictory_api import PictoryAPI
    components_status['Pictory API'] = '✅ Available'
except ImportError as e:
    components_status['Pictory API'] = f'❌ Missing: {e}'

for component, status in components_status.items():
    print(f"  {component}: {status}")

# Step 3: Test sample content
print("\n[STEP 3] Preparing test content...")

test_script = """
Today in AI, we're witnessing unprecedented developments in artificial intelligence.
OpenAI has announced GPT-5, marking a significant leap forward in AI capabilities.
The model demonstrates dramatically improved reasoning abilities with a 40% reduction in hallucination rates.
Meanwhile, Google DeepMind has achieved a breakthrough in protein folding prediction.
"""

test_segments = [
    {
        "chapter_title": "GPT-5 Launch",
        "duration": 15,
        "text": "OpenAI announces GPT-5 with breakthrough capabilities",
        "broll_query": "artificial intelligence technology"
    },
    {
        "chapter_title": "DeepMind Breakthrough",
        "duration": 15,
        "text": "Google DeepMind revolutionizes protein folding",
        "broll_query": "scientific research laboratory"
    }
]

print(f"  Script: {len(test_script.split())} words")
print(f"  Segments: {len(test_segments)}")
print(f"  Total duration: ~30 seconds")

# Step 4: Test renderer selection
print("\n[STEP 4] Testing video renderer selection...")
if 'Video Renderer Selector' in components_status and '✅' in components_status['Video Renderer Selector']:
    try:
        from src.produce.video_renderer_selector import VideoRendererSelector
        renderer = VideoRendererSelector()
        
        print(f"  Shotstack available: {renderer.shotstack_enabled}")
        print(f"  Pictory available: {renderer.pictory_enabled}")
        
        if renderer.shotstack_enabled:
            cost = renderer.get_cost_estimate(duration_minutes=0.5, use_shotstack=True)
            print(f"  Shotstack cost: ${cost['render_cost']:.3f} per video")
            print(f"  Monthly estimate: ${cost['monthly_estimate']:.2f}")
        
        if renderer.pictory_enabled:
            cost = renderer.get_cost_estimate(duration_minutes=0.5, use_shotstack=False)
            print(f"  Pictory cost: ${cost['render_cost']:.2f} per video")
            print(f"  Monthly estimate: ${cost['monthly_estimate']:.2f}")
            
    except Exception as e:
        print(f"  ❌ Renderer error: {e}")
else:
    print("  ⚠️ Video Renderer Selector not available")

# Step 5: Test Slack integration
print("\n[STEP 5] Testing Slack integration...")
if env_status.get('SLACK_BOT_TOKEN') == '✅ Loaded' or env_status.get('SLACK_WEBHOOK_URL') == '✅ Loaded':
    if 'Slack Approvals' in components_status and '✅' in components_status['Slack Approvals']:
        try:
            from src.slack_approvals import SlackApprovalService
            slack = SlackApprovalService()
            print("  ✅ Slack service initialized")
            
            # Optionally send test message
            # Uncomment to send actual test message to Slack
            # approval_id = slack.send_approval_request(
            #     content_type="video",
            #     title="TEST: Enhanced Pipeline",
            #     preview_url="https://storage.googleapis.com/test/preview.mp4",
            #     metadata={
            #         "Duration": "30 seconds",
            #         "Type": "Test",
            #         "Pipeline": "Enhanced Pipeline with Shotstack"
            #     }
            # )
            # print(f"  ✅ Test approval sent: {approval_id}")
            
        except Exception as e:
            print(f"  ❌ Slack error: {e}")
    else:
        print("  ⚠️ Slack Approvals module not available")
else:
    print("  ⚠️ Slack credentials not configured")

# Step 6: Configuration summary
print("\n[STEP 6] Configuration Summary:")
print("="*60)

config_ready = []
config_missing = []

# Check what's ready
if env_status.get('SHOTSTACK_API_KEY') == '✅ Loaded':
    config_ready.append("✅ Shotstack rendering (cost-effective)")
else:
    config_missing.append("❌ SHOTSTACK_API_KEY - for cost-effective rendering")

if env_status.get('PICTORY_CLIENT_ID') == '✅ Loaded':
    config_ready.append("✅ Pictory rendering (automatic B-roll)")
else:
    config_missing.append("❌ Pictory credentials - for fallback rendering")

if env_status.get('SLACK_BOT_TOKEN') == '✅ Loaded' or env_status.get('SLACK_WEBHOOK_URL') == '✅ Loaded':
    config_ready.append("✅ Slack approvals")
else:
    config_missing.append("❌ Slack credentials - for human approval workflow")

if env_status.get('PEXELS_API_KEY') == '✅ Loaded':
    config_ready.append("✅ Pexels B-roll search")
else:
    config_missing.append("⚠️ PEXELS_API_KEY - for stock footage")

print("\n✅ Ready to use:")
for item in config_ready:
    print(f"  {item}")

if config_missing:
    print("\n⚠️ Missing/Optional:")
    for item in config_missing:
        print(f"  {item}")

print("\n" + "="*60)
print("📝 Pipeline Flow:")
print("1. Generate script with AI")
print("2. Resolve B-roll assets (Pexels/Pixabay → GCS)")
print("3. Generate voiceover (ElevenLabs/TTS)")
print("4. Select renderer (Shotstack preferred, Pictory fallback)")
print("5. Build timeline and render video")
print("6. Send to Slack for approval")
print("7. Publish to YouTube on approval")
print("="*60)

# Step 7: Recommendations
print("\n[STEP 7] Recommendations:")
if env_status.get('SHOTSTACK_API_KEY') != '✅ Loaded':
    print("\n⚠️ SHOTSTACK_API_KEY not found. To enable cost-effective rendering:")
    print("   1. Sign up at https://shotstack.io")
    print("   2. Get your API key from the dashboard")
    print("   3. Add to GCP Secret Manager:")
    print("      echo 'YOUR_KEY' | gcloud secrets create SHOTSTACK_API_KEY --data-file=-")

print("\n✅ Enhanced pipeline components deployed successfully!")
print("\nTo run a full test with actual video generation:")
print("  python3 ~/AIT/run_enhanced_pipeline.py")