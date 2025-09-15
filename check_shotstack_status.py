#!/usr/bin/env python3
import os
import sys
import subprocess
import httpx
import json

# Load Shotstack API key
try:
    api_key = subprocess.check_output(
        ['gcloud', 'secrets', 'versions', 'access', 'latest', '--secret=SHOTSTACK_API_KEY'],
        stderr=subprocess.DEVNULL
    ).decode().strip()
    os.environ['SHOTSTACK_API_KEY'] = api_key
except:
    print('Error loading SHOTSTACK_API_KEY')
    sys.exit(1)

# The render ID from the last attempt (you mentioned it in the error)
render_id = 'f2f2683e-766e-442a-87d0-acc5518aac7c'

print(f'Checking status for render: {render_id}')
print('='*60)

headers = {'x-api-key': api_key}
url = f'https://api.shotstack.io/v1/render/{render_id}'

try:
    with httpx.Client(timeout=30) as client:
        response = client.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json().get('response', {})
            
            print(f"Status: {data.get('status')}" )
            print(f"Created: {data.get('created')}")
            print(f"Updated: {data.get('updated')}")
            
            if data.get('status') == 'completed':
                print(f"\n✅ RENDER COMPLETED!")
                print(f"URL: {data.get('url')}")
                print(f"Duration: {data.get('duration')} seconds")
                print(f"Credits used: {data.get('credits')}")
            elif data.get('status') == 'failed':
                print(f"\n❌ RENDER FAILED")
                print(f"Error: {data.get('error')}")
            elif data.get('status') in ['queued', 'rendering']:
                print(f"\n⏳ STILL PROCESSING")
                print(f"Progress: {data.get('renderProgress', 0)}%")
            
            print(f"\nFull response:")
            print(json.dumps(data, indent=2))
        else:
            print(f'Error: {response.status_code}')
            print(response.text)
except Exception as e:
    print(f'Error checking status: {e}')
