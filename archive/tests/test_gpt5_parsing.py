#!/usr/bin/env python3
"""Test GPT-5 shot list generation and parsing"""

import os
import subprocess
import json
import re
from openai import OpenAI

# Load API key
api_key = subprocess.check_output(
    ['gcloud', 'secrets', 'versions', 'access', 'latest', '--secret=OPENAI_API_KEY'],
    stderr=subprocess.DEVNULL
).decode().strip()

client = OpenAI(api_key=api_key)

# Simple test script
test_script = """
Welcome to Today in AI. OpenAI has unveiled GPT-5 with revolutionary reasoning capabilities. 
Google DeepMind achieves breakthrough in protein prediction.
Meta releases open-source model rivaling GPT-4 performance.
"""

# Simpler prompt for GPT-5
simple_prompt = """
You are a video producer. Generate a shot list for this script. 
For each sentence, create one shot with keywords and style.
Format as a markdown table with columns: Timestamp | Voiceover | B-Roll Shot List

Script:
""" + test_script

print("Testing GPT-5 shot list generation and parsing...")
print("=" * 60)

try:
    # Test with GPT-5
    response = client.chat.completions.create(
        model="gpt-5",
        messages=[
            {"role": "system", "content": "You are a professional video producer."},
            {"role": "user", "content": simple_prompt}
        ],
        max_completion_tokens=2000
    )
    
    content = response.choices[0].message.content
    print("GPT-5 Response:")
    print("-" * 60)
    print(content)
    print("-" * 60)
    
    # Test the parsing logic from shot_list_generator.py
    print("\nParsing with current logic:")
    segments = []
    lines = content.split('\n')
    
    for line in lines:
        if '|' in line and 'Timestamp' not in line and '---' not in line:
            parts = line.split('|')
            if len(parts) >= 4:
                print(f"Found line with {len(parts)} parts: {line[:80]}")
                timestamp = parts[1].strip()
                voiceover = parts[2].strip()
                shots_text = parts[3].strip()
                
                print(f"  Timestamp: {timestamp}")
                print(f"  Voiceover: {voiceover[:50]}...")
                print(f"  Shots text: {shots_text[:50]}...")
                
                segments.append({
                    'timestamp': timestamp,
                    'voiceover': voiceover,
                    'shots_text': shots_text
                })
    
    print(f"\nParsed {len(segments)} segments")
    
    # Alternative parsing for tables with 3 columns
    if len(segments) == 0:
        print("\nTrying alternative parsing (3 columns):")
        for line in lines:
            if '|' in line and 'Timestamp' not in line and '---' not in line:
                parts = line.split('|')
                # Remove empty parts from start/end
                parts = [p for p in parts if p.strip()]
                if len(parts) >= 3:
                    print(f"Found line with {len(parts)} parts: {line[:80]}")
                    timestamp = parts[0].strip()
                    voiceover = parts[1].strip()
                    shots_text = parts[2].strip() if len(parts) > 2 else ""
                    
                    segments.append({
                        'timestamp': timestamp,
                        'voiceover': voiceover,
                        'shots_text': shots_text
                    })
        
        print(f"Alternative parsing found {len(segments)} segments")
    
    # Save for analysis
    with open('/tmp/gpt5_parsing_test.json', 'w') as f:
        json.dump({
            'raw_response': content,
            'parsed_segments': segments,
            'line_count': len(lines),
            'table_lines': [l for l in lines if '|' in l]
        }, f, indent=2)
    
    print("\nTest data saved to /tmp/gpt5_parsing_test.json")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

