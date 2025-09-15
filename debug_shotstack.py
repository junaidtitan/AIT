#!/usr/bin/env python3
import os, sys, subprocess, json, httpx
sys.path.insert(0, '/home/junaidqureshi/AIT')

api_key = subprocess.check_output(
    ['gcloud', 'secrets', 'versions', 'access', 'latest', '--secret=SHOTSTACK_API_KEY'],
    stderr=subprocess.DEVNULL
).decode().strip()

print('Debugging Shotstack render status...')
print()

# Test minimal render
payload = {
    'timeline': {
        'tracks': [
            {
                'clips': [
                    {
                        'asset': {
                            'type': 'title',
                            'text': 'Test Video',
                            'style': 'minimal'
                        },
                        'start': 0,
                        'length': 5
                    }
                ]
            }
        ]
    },
    'output': {
        'format': 'mp4',
        'resolution': 'hd'
    }
}

headers = {
    'x-api-key': api_key,
    'Content-Type': 'application/json'
}

with httpx.Client(timeout=30) as client:
    # Submit render
    print('Submitting minimal test render...')
    response = client.post(
        'https://api.shotstack.io/v1/render',
        content=json.dumps(payload),
        headers=headers
    )
    
    if response.status_code >= 300:
        print(f'Submit failed: {response.status_code}')
        print(response.text)
        sys.exit(1)
    
    render_id = response.json().get('response', {}).get('id')
    print(f'Render ID: {render_id}')
    print()
    
    # Check status
    import time
    for i in range(20):
        response = client.get(
            f'https://api.shotstack.io/v1/render/{render_id}',
            headers={'x-api-key': api_key}
        )
        
        if response.status_code >= 300:
            print(f'Status check failed: {response.status_code}')
            break
        
        data = response.json().get('response', {})
        status = data.get('status')
        progress = data.get('renderProgress', 0)
        
        print(f'[{i+1}/20] Status: {status}, Progress: {progress}%')
        
        if status == 'done':
            url = data.get('url')
            if url:
                print(f'\n✅ Success! Video URL: {url}')
            else:
                print('\n⚠️ Status is done but no URL in response')
                print(f'Full response: {json.dumps(data, indent=2)}')
            break
        elif status == 'failed':
            print(f'\n❌ Render failed')
            print(f'Error: {data.get("error")}')
            print(f'Full response: {json.dumps(data, indent=2)}')
            break
        
        time.sleep(3)
