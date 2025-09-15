#!/usr/bin/env python3
import os, sys, subprocess, json, httpx
sys.path.insert(0, '/home/junaidqureshi/AIT')

# Load API key
api_key = subprocess.check_output(
    ['gcloud', 'secrets', 'versions', 'access', 'latest', '--secret=SHOTSTACK_API_KEY'],
    stderr=subprocess.DEVNULL
).decode().strip()

print('Testing Shotstack API directly...')
print()

# Get recent renders
headers = {'x-api-key': api_key}
with httpx.Client(timeout=30) as client:
    # List recent renders
    response = client.get(
        'https://api.shotstack.io/v1/render',
        headers=headers,
        params={'limit': 5}
    )
    
    if response.status_code == 200:
        data = response.json()
        renders = data.get('data', [])
        
        print(f'Found {len(renders)} recent renders:')
        print()
        
        for render in renders[:3]:  # Show last 3
            print(f"ID: {render.get('id')}" )
            print(f"Status: {render.get('status')}" )
            print(f"Created: {render.get('created')}" )
            
            # Get detailed status
            detail_resp = client.get(
                f"https://api.shotstack.io/v1/render/{render.get('id')}",
                headers=headers
            )
            if detail_resp.status_code == 200:
                detail = detail_resp.json().get('response', {})
                print(f"Progress: {detail.get('renderProgress', 0)}%" )
                
                if detail.get('status') == 'failed':
                    print(f"Error: {detail.get('error', 'Unknown')}" )
                elif detail.get('status') == 'done':
                    url = detail.get('url')
                    if url:
                        print(f"✅ Video URL: {url}" )
                    else:
                        print('⚠️ Status is done but no URL provided')
                        print(f"Full response: {json.dumps(detail, indent=2)}" )
            print('-' * 40)
    else:
        print(f'API error: {response.status_code}')
        print(response.text)
