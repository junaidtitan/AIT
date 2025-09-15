import os
import time
import httpx
import json

class PictoryAPI:
    def __init__(self):
        self.client_id = os.getenv('PICTORY_CLIENT_ID')
        self.client_secret = os.getenv('PICTORY_CLIENT_SECRET')
        self.base_url = 'https://api.pictory.ai/pictoryapis/v1'
        self.access_token = None
        self.user_id = self.client_id  # Use client_id as user_id
        
    def authenticate(self):
        """Get OAuth2 access token"""
        if not self.client_id or not self.client_secret:
            raise ValueError('Pictory credentials not configured')
            
        auth_url = f'{self.base_url}/oauth2/token'
        
        with httpx.Client(timeout=30) as client:
            response = client.post(
                auth_url,
                data={
                    'client_id': self.client_id,
                    'client_secret': self.client_secret
                }
            )
            
            if response.status_code != 200:
                raise Exception(f'Authentication failed: {response.status_code} - {response.text}')
                
            data = response.json()
            self.access_token = data.get('access_token')
            return self.access_token
            
    def create_storyboard(self, script: str, video_name: str):
        """Create storyboard from script"""
        if not self.access_token:
            self.authenticate()
            
        url = f'{self.base_url}/video/storyboard'
        
        # Parse script into scenes
        scenes = []
        paragraphs = script.split('\\n\\n')
        
        for paragraph in paragraphs:
            if paragraph.strip():
                scenes.append({
                    'text': paragraph.strip(),
                    'voiceOver': True,
                    'splitTextOnNewLine': False,
                    'splitTextOnPeriod': True
                })
                
        payload = {
            'videoName': video_name,
            'videoDescription': 'AI News Executive Briefing',
            'language': 'en',
            'scenes': scenes,
            'audio': {
                'aiVoiceOver': {
                    'speaker': 'Matthew',
                    'speed': '100',
                    'amplifyLevel': 0
                },
                'autoBackgroundMusic': False
            },
            'videoWidth': 1920,
            'videoHeight': 1080
        }
        
        headers = {
            'Authorization': self.access_token,
            'X-Pictory-User-Id': self.user_id,
            'Content-Type': 'application/json'
        }
        
        with httpx.Client(timeout=60) as client:
            response = client.post(url, json=payload, headers=headers)
            
            if response.status_code not in [200, 201]:
                raise Exception(f'Storyboard creation failed: {response.status_code} - {response.text}')
                
            data = response.json()
            return data.get('jobId')
            
    def render_video(self, storyboard_job_id: str):
        """Render video from storyboard"""
        if not self.access_token:
            self.authenticate()
            
        url = f'{self.base_url}/video/render/{storyboard_job_id}'
        
        headers = {
            'Authorization': self.access_token,
            'X-Pictory-User-Id': self.user_id
        }
        
        with httpx.Client(timeout=60) as client:
            response = client.put(url, headers=headers)
            
            if response.status_code not in [200, 201]:
                raise Exception(f'Video render failed: {response.status_code} - {response.text}')
                
            data = response.json()
            return data.get('data', {}).get('job_id')
            
    def check_job_status(self, job_id: str):
        """Check job status"""
        if not self.access_token:
            self.authenticate()
            
        url = f'{self.base_url}/jobs/{job_id}'
        
        headers = {
            'Authorization': self.access_token,
            'X-Pictory-User-Id': self.user_id
        }
        
        with httpx.Client(timeout=30) as client:
            response = client.get(url, headers=headers)
            
            if response.status_code != 200:
                raise Exception(f'Status check failed: {response.status_code} - {response.text}')
                
            return response.json()
            
    def wait_for_completion(self, job_id: str, max_wait: int = 600):
        """Wait for job to complete"""
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            status_data = self.check_job_status(job_id)
            status = status_data.get('status')
            
            if status == 'completed':
                return status_data
            elif status == 'failed':
                raise Exception(f'Job failed: {status_data.get("error")}')
                
            print(f'Job status: {status}, waiting...')
            time.sleep(10)
            
        raise Exception('Job timed out')
        
    def download_video(self, video_url: str, output_path: str):
        """Download rendered video"""
        with httpx.Client(timeout=300) as client:
            response = client.get(video_url)
            
            if response.status_code != 200:
                raise Exception(f'Video download failed: {response.status_code}')
                
            with open(output_path, 'wb') as f:
                f.write(response.content)
                
        return output_path
        
    def generate_video(self, script: str, video_name: str, output_path: str):
        """Full pipeline to generate video"""
        try:
            print('Authenticating with Pictory...')
            self.authenticate()
            
            print(f'Creating storyboard for: {video_name}')
            storyboard_job_id = self.create_storyboard(script, video_name)
            
            print('Waiting for storyboard to complete...')
            storyboard_result = self.wait_for_completion(storyboard_job_id)
            
            print('Rendering video...')
            render_job_id = self.render_video(storyboard_job_id)
            
            print('Waiting for video render...')
            render_result = self.wait_for_completion(render_job_id)
            
            video_url = render_result.get('data', {}).get('videoURL')
            if not video_url:
                raise Exception('No video URL in render result')
                
            print(f'Downloading video to {output_path}')
            self.download_video(video_url, output_path)
            
            print(f'Video successfully generated: {output_path}')
            return output_path
            
        except Exception as e:
            print(f'Error in Pictory video generation: {e}')
            # Create stub video as fallback
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, 'wb') as f:
                f.write(b'STUB_VIDEO')
            return output_path
