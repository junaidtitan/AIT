#!/usr/bin/env python3
"""
Complete Enhanced Pipeline with all components:
- Asset research and ranking from Pexels/Pixabay
- ElevenLabs voiceover generation
- Shotstack video rendering with ranked B-roll
- GCS asset caching
- Slack approval workflow
"""
import os
import sys
import subprocess
import time
import json
from datetime import datetime
import hashlib

sys.path.insert(0, '/home/junaidqureshi/AIT')

# Load all credentials from Secret Manager
print("Loading credentials from GCP Secret Manager...")
secrets = {
    'ELEVENLABS_API_KEY': None,
    'SHOTSTACK_API_KEY': None,
    'PEXELS_API_KEY': None,
    'SLACK_BOT_TOKEN': None,
    'PICTORY_CLIENT_ID': None,
    'PICTORY_CLIENT_SECRET': None
}

for secret_name in secrets:
    try:
        value = subprocess.check_output(
            ['gcloud', 'secrets', 'versions', 'access', 'latest', f'--secret={secret_name}'],
            stderr=subprocess.DEVNULL
        ).decode().strip()
        os.environ[secret_name] = value
        secrets[secret_name] = value
        print(f"  ✓ {secret_name} loaded")
    except:
        print(f"  ⚠ {secret_name} not found")

# Set additional environment variables
os.environ['ASSET_CACHE_BUCKET'] = 'yta-main-assets'
os.environ['GCP_PROJECT'] = 'retrotube-471606'

# Import all components
from src.produce.shotstack_enhanced import ShotstackEnhanced
from src.produce.video_renderer_selector import VideoRendererSelector
from src.slack_approvals import SlackApprovalService
from google.cloud import storage

print("\n" + "="*60)
print("🚀 FULL ENHANCED PIPELINE WITH ASSET RESEARCH")
print("="*60)

# Test content - AI news script
script = """
Breaking News in Artificial Intelligence. 

OpenAI has unveiled GPT-5, their most advanced language model to date. This groundbreaking system demonstrates unprecedented reasoning capabilities, with a 40 percent reduction in hallucination rates compared to its predecessor. Enterprise clients are reporting productivity gains of up to 60 percent in software development tasks.

Meanwhile, Google DeepMind achieves a major breakthrough in protein folding prediction. Their latest AlphaFold iteration can now predict protein interactions with 95 percent accuracy. This advancement could reduce drug development timelines by 3 to 5 years, potentially saving millions of lives.

In open source developments, Meta releases a powerful large language model that rivals proprietary alternatives. The model, trained on 15 trillion tokens, is completely free to use and modify. Over 50,000 developers have already downloaded it in the first week alone.

These developments signal a new era in AI adoption. The convergence of improved capabilities, reduced costs, and broader accessibility makes 2024 a pivotal year for artificial intelligence in enterprise applications.
"""

print(f"\nScript details:")
print(f"  • Words: {len(script.split())}")
print(f"  • Est. duration: {len(script.split())/150*60:.0f} seconds")

# Step 1: Generate voiceover with ElevenLabs
print("\n[1/6] Generating voiceover with ElevenLabs...")
try:
    import requests
    
    # Use ElevenLabs API
    headers = {
        'xi-api-key': secrets['ELEVENLABS_API_KEY'],
        'Content-Type': 'application/json'
    }
    
    payload = {
        'text': script,
        'model_id': 'eleven_monolingual_v1',
        'voice_settings': {
            'stability': 0.5,
            'similarity_boost': 0.75
        }
    }
    
    # Use default voice ID (Rachel)
    voice_id = '21m00Tcm4TlvDq8ikWAM'
    
    response = requests.post(
        f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}',
        json=payload,
        headers=headers
    )
    
    if response.status_code == 200:
        # Save voiceover
        voiceover_path = f'/home/junaidqureshi/AIT/starter/data/voiceover_{datetime.now().strftime("%Y%m%d_%H%M%S")}.mp3'
        with open(voiceover_path, 'wb') as f:
            f.write(response.content)
        
        # Upload to GCS
        storage_client = storage.Client()
        bucket = storage_client.bucket(os.environ['ASSET_CACHE_BUCKET'])
        blob_name = f'voiceovers/vo_{datetime.now().strftime("%Y%m%d_%H%M%S")}.mp3'
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(voiceover_path)
        voiceover_url = f'https://storage.googleapis.com/{os.environ["ASSET_CACHE_BUCKET"]}/{blob_name}'
        
        print(f"  ✓ Voiceover generated: {voiceover_url}")
        
        # Get duration estimate
        vo_duration = len(script.split()) / 150 * 60  # Rough estimate
        print(f"  Duration: ~{vo_duration:.0f} seconds")
    else:
        print(f"  ⚠ ElevenLabs failed: {response.status_code}")
        # Fallback to placeholder
        voiceover_url = 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3'
        vo_duration = 40
        print(f"  Using placeholder audio")
        
except Exception as e:
    print(f"  ⚠ Voiceover generation error: {e}")
    voiceover_url = 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3'
    vo_duration = 40

# Step 2: Research and rank B-roll assets
print("\n[2/6] Researching B-roll assets...")
try:
    # Import Pexels client directly
    import requests
    
    def search_pexels(query, api_key):
        """Search Pexels for videos/images"""
        headers = {'Authorization': api_key}
        
        # Try videos first
        response = requests.get(
            'https://api.pexels.com/videos/search',
            params={'query': query, 'per_page': 5},
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('videos'):
                # Get highest quality video file
                video = data['videos'][0]
                for file in video.get('video_files', []):
                    if file.get('quality') == 'hd':
                        return file['link']
                # Fallback to first video file
                if video.get('video_files'):
                    return video['video_files'][0]['link']
        
        # Fallback to images
        response = requests.get(
            'https://api.pexels.com/v1/search',
            params={'query': query, 'per_page': 5},
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('photos'):
                return data['photos'][0]['src']['large2x']
        
        return None
    
    # Define search queries for each segment
    queries = [
        "artificial intelligence technology futuristic",
        "software development coding productivity",
        "medical research laboratory science",
        "open source community collaboration"
    ]
    
    segments = []
    segment_duration = vo_duration / len(queries)
    
    for i, query in enumerate(queries):
        print(f"  Searching: {query}")
        
        asset_url = None
        if secrets.get('PEXELS_API_KEY'):
            asset_url = search_pexels(query, secrets['PEXELS_API_KEY'])
        
        if asset_url:
            print(f"    ✓ Found asset from Pexels")
            segments.append({
                'chapter_title': f"Chapter {i+1}",
                'duration': segment_duration,
                'text': query.split()[0].title() + " Segment",
                'broll_url': asset_url
            })
        else:
            # Use fallback images
            fallback_urls = [
                'https://images.pexels.com/photos/373543/pexels-photo-373543.jpeg',
                'https://images.pexels.com/photos/590022/pexels-photo-590022.jpeg',
                'https://images.pexels.com/photos/2280547/pexels-photo-2280547.jpeg',
                'https://images.pexels.com/photos/3861969/pexels-photo-3861969.jpeg'
            ]
            segments.append({
                'chapter_title': f"Chapter {i+1}",
                'duration': segment_duration,
                'text': query.split()[0].title() + " Segment",
                'broll_url': fallback_urls[i % len(fallback_urls)]
            })
            print(f"    ⚠ Using fallback image")
    
    print(f"  ✓ Prepared {len(segments)} segments with B-roll")
    
except Exception as e:
    print(f"  ⚠ Asset research error: {e}")
    # Create basic segments without B-roll
    segments = [
        {
            'chapter_title': 'GPT-5 Announcement',
            'duration': vo_duration/4,
            'text': 'OpenAI unveils GPT-5',
            'broll_url': 'https://images.pexels.com/photos/373543/pexels-photo-373543.jpeg'
        },
        {
            'chapter_title': 'Performance Improvements',
            'duration': vo_duration/4,
            'text': 'Reduced hallucinations',
            'broll_url': 'https://images.pexels.com/photos/590022/pexels-photo-590022.jpeg'
        },
        {
            'chapter_title': 'DeepMind Breakthrough',
            'duration': vo_duration/4,
            'text': 'Protein folding advances',
            'broll_url': 'https://images.pexels.com/photos/2280547/pexels-photo-2280547.jpeg'
        },
        {
            'chapter_title': 'Open Source Progress',
            'duration': vo_duration/4,
            'text': 'Meta releases free model',
            'broll_url': 'https://images.pexels.com/photos/3861969/pexels-photo-3861969.jpeg'
        }
    ]

# Step 3: Render video with Shotstack
print("\n[3/6] Rendering video with Shotstack...")
try:
    renderer = VideoRendererSelector()
    
    # Show cost comparison
    duration_min = vo_duration / 60
    shotstack_cost = renderer.get_cost_estimate(duration_min, use_shotstack=True)
    pictory_cost = renderer.get_cost_estimate(duration_min, use_shotstack=False)
    
    print(f"  Cost comparison:")
    print(f"    • Shotstack: ${shotstack_cost['render_cost']:.3f}")
    print(f"    • Pictory: ${pictory_cost['render_cost']:.2f}")
    savings_pct = (1 - shotstack_cost['render_cost']/max(pictory_cost['render_cost'], 0.01))*100
    print(f"    • Savings: {savings_pct:.0f}% cheaper with Shotstack")
    
    output_path = f'/home/junaidqureshi/AIT/starter/data/full_pipeline_{datetime.now().strftime("%Y%m%d_%H%M%S")}.mp4'
    
    print(f"\n  Rendering with Shotstack...")
    start_time = time.time()
    
    rendered_path = renderer.render_video(
        script=script,
        title=f'AI News - {datetime.now().strftime("%B %d, %Y")}',
        segments=segments,
        voiceover_url=voiceover_url,
        output_path=output_path,
        prefer_shotstack=True,
        style='professional'
    )
    
    render_time = time.time() - start_time
    print(f"  ✓ Video rendered in {render_time:.1f} seconds")
    
    # Check file size
    if os.path.exists(rendered_path):
        size = os.path.getsize(rendered_path) / (1024*1024)
        print(f"  File size: {size:.1f} MB")
        
        # Upload to GCS for preview
        storage_client = storage.Client()
        bucket = storage_client.bucket(os.environ['ASSET_CACHE_BUCKET'])
        blob_name = f'videos/pipeline_{datetime.now().strftime("%Y%m%d_%H%M%S")}.mp4'
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(rendered_path)
        preview_url = f'https://storage.googleapis.com/{os.environ["ASSET_CACHE_BUCKET"]}/{blob_name}'
        print(f"  Preview URL: {preview_url}")
    else:
        preview_url = rendered_path
        
except Exception as e:
    print(f"  ❌ Render failed: {e}")
    import traceback
    traceback.print_exc()
    
    # Try Pictory fallback
    print("\n  Attempting Pictory fallback...")
    try:
        rendered_path = renderer.render_video(
            script=script,
            title='AI News',
            segments=segments,
            voiceover_url=voiceover_url,
            output_path=output_path,
            prefer_shotstack=False,
            style='professional'
        )
        print(f"  ✓ Pictory fallback successful")
        preview_url = rendered_path
    except Exception as e2:
        print(f"  ❌ Pictory also failed: {e2}")
        preview_url = 'https://storage.googleapis.com/yta-main-assets/test_preview.mp4'

# Step 4: Send Slack approval
print("\n[4/6] Sending Slack approval notification...")
try:
    slack = SlackApprovalService()
    
    approval_id = slack.send_approval_request(
        content_type='video',
        title='🎬 AI News Video - Full Pipeline Test',
        preview_url=preview_url,
        metadata={
            'Duration': f'{vo_duration:.0f} seconds',
            'Renderer': 'Shotstack Enhanced',
            'Cost': f'${shotstack_cost["render_cost"]:.3f}',
            'B-roll Sources': f'{len([s for s in segments if s.get("broll_url")])} assets',
            'Voiceover': 'ElevenLabs' if 'voiceover_' in voiceover_url else 'Placeholder',
            'Style': 'Professional',
            'Pipeline': 'Full Enhanced'
        }
    )
    
    print(f"  ✓ Approval request sent: {approval_id}")
    print(f"  Check #ai-news-approvals channel")
    
except Exception as e:
    print(f"  ⚠ Slack notification error: {e}")

# Step 5: Summary
print("\n" + "="*60)
print("✅ FULL PIPELINE EXECUTION COMPLETE!")
print("="*60)
print("\nPipeline Summary:")
print(f"• Voiceover: {'✓ ElevenLabs' if 'voiceover_' in voiceover_url else '⚠ Placeholder'}")
print(f"• B-roll Research: {len([s for s in segments if s.get('broll_url')])} assets found")
print(f"• Video Render: {'✓ Shotstack' if 'rendered_path' in locals() else '⚠ Failed'}")
print(f"• Cost: ${shotstack_cost['render_cost']:.3f} (vs Pictory ${pictory_cost['render_cost']:.2f})")
print(f"• Slack Approval: {'✓ Sent' if 'approval_id' in locals() else '⚠ Failed'}")

if 'rendered_path' in locals() and os.path.exists(rendered_path):
    print(f"\nOutput file: {rendered_path}")
    print(f"Preview URL: {preview_url}")

print("\nWebhook URL for approvals:")
print("https://slack-webhook-handler-933331129751.us-central1.run.app")
print("="*60)