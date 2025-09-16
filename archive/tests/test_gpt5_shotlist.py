#!/usr/bin/env python3
"""Test GPT-5 shot list generation to debug the issue"""

import os
import subprocess
import json
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

print("Testing GPT-5 shot list generation...")
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
    
    # Save raw response
    with open('/tmp/gpt5_response.txt', 'w') as f:
        f.write(content)
    print("\nRaw response saved to /tmp/gpt5_response.txt")
    
    # Try parsing
    print("\nParsing attempt:")
    lines = content.split('\n')
    table_lines = []
    in_table = False
    
    for line in lines:
        if '|' in line:
            if 'Timestamp' in line:
                in_table = True
            elif in_table and '---' not in line:
                table_lines.append(line)
    
    print(f"Found {len(table_lines)} table lines")
    for i, line in enumerate(table_lines[:3]):
        print(f"  Line {i+1}: {line[:80]}...")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

