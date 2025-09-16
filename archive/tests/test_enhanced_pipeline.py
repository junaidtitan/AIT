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

