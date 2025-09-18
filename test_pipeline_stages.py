#!/usr/bin/env python3
"""Test pipeline stages individually"""

import os
import sys

# Load secrets
api_key = os.popen('gcloud secrets versions access latest --secret=OPENAI_API_KEY 2>/dev/null').read().strip()
os.environ['OPENAI_API_KEY'] = api_key
os.environ['ELEVENLABS_API_KEY'] = os.popen('gcloud secrets versions access latest --secret=ELEVENLABS_API_KEY 2>/dev/null').read().strip()
os.environ['ELEVENLABS_VOICE_ID'] = 'ygkaO6a4xYPwmJY5LCz9'
os.environ['USE_SHEETS_SOURCES'] = 'false'

print("=" * 80)
print("TESTING PIPELINE STAGES")
print("=" * 80)

# Stage 1: Test Script Generation (we know this works)
print("\n1. Script Generation Test...")
sample_stories = [
    {
        'title': 'OpenAI Releases GPT-5',
        'summary': 'Major breakthrough in AI capabilities',
        'url': 'http://example.com',
        'source_domain': 'OpenAI Blog',
        'full_text': 'OpenAI announced GPT-5 today with unprecedented capabilities.'
    }
]

from src.editorial.script_daily import ScriptGenerator
generator = ScriptGenerator()
script = generator.generate_script(sample_stories)

if script and script.get('vo_script'):
    print(f"   ✓ Script generated: {len(script['vo_script'])} chars")
    script_text = script['vo_script']
else:
    print("   ✗ Script generation failed")
    sys.exit(1)

# Stage 2: Test Shot List Generation (this is hanging)
print("\n2. Shot List Generation Test...")
print("   Testing with timeout...")

import signal
import time

def timeout_handler(signum, frame):
    raise TimeoutError("Shot list generation timed out")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(10)  # 10 second timeout

try:
    from src.produce.shot_list_generator import ShotListGenerator
    shot_gen = ShotListGenerator()

    # Try with a simple script
    simple_script = "Today in AI news. OpenAI released GPT-5. That's all for today."

    print("   Attempting shot list generation...")
    shots = shot_gen.generate_shot_list(simple_script, 10.0)

    signal.alarm(0)  # Cancel timeout

    if shots:
        print(f"   ✓ Shot list generated: {len(shots)} segments")
    else:
        print("   ✗ No shots generated")

except TimeoutError:
    print("   ✗ Shot list generation hung (timed out after 10s)")
    print("   This is the stage causing the pipeline to hang")
    signal.alarm(0)

except Exception as e:
    print(f"   ✗ Shot list error: {e}")
    signal.alarm(0)

print("\n" + "=" * 80)
print("STAGE TEST COMPLETE")
print("=" * 80)