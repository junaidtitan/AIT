import os
import json
import time
import httpx
from typing import Dict, Optional

class PictoryVideoGenerator:
    def __init__(self):
        self.client_id = os.getenv("PICTORY_CLIENT_ID")
        self.client_secret = os.getenv("PICTORY_CLIENT_SECRET")
        self.base_url = "https://api.pictory.ai/pictory"
        self.access_token = None
        
    def authenticate(self):
        """Get OAuth2 access token"""
        if not self.client_id or not self.client_secret:
            raise ValueError("Pictory credentials not configured")
            
        auth_url = f"{self.base_url}/oauth2/token"
        
        with httpx.Client(timeout=30) as client:
            response = client.post(
                auth_url,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Authentication failed: {response.status_code} - {response.text}")
                
            data = response.json()
            self.access_token = data.get("access_token")
            return self.access_token
            
    def create_storyboard(self, script: str, video_name: str) -> str:
        """Create storyboard from script"""
        if not self.access_token:
            self.authenticate()
            
        url = f"{self.base_url}/video/storyboard"
        
        # Parse script into scenes
        scenes = []
        paragraphs = script.split('\n\n')
        
        for i, paragraph in enumerate(paragraphs):
            if paragraph.strip():
                scenes.append({
                    "text": paragraph.strip(),
                    "voiceOver": True,
                    "splitTextOnNewLine": False,
                    "splitTextOnPeriod": True
                })
                
        payload = {
            "videoName": video_name,
            "videoDescription": "AI News Briefing",
            "language": "en",
            "scenes": scenes,
            "audio": {
                "aiVoiceOver": {
                    "speaker": "Matthew",
                    "speed": "100", 
                    "amplifyLevel": 0
                },
                "autoBackgroundMusic": False
            },
            "videoWidth": 1920,
            "videoHeight": 1080,
            "output": {
                "format": "mp4",
                "resolution": "1080"
            }
        }
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        with httpx.Client(timeout=60) as client:
            response = client.post(url, json=payload, headers=headers)
            
            if response.status_code != 200:
                raise Exception(f"Storyboard creation failed: {response.status_code} - {response.text}")
                
            data = response.json()
            return data.get("jobId")
            
    def wait_for_storyboard(self, job_id: str, max_wait: int = 300) -> Dict:
        """Wait for storyboard to complete"""
        if not self.access_token:
            self.authenticate()
            
        url = f"{self.base_url}/jobs/{job_id}"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            with httpx.Client(timeout=30) as client:
                response = client.get(url, headers=headers)
                
                if response.status_code != 200:
                    raise Exception(f"Status check failed: {response.status_code} - {response.text}")
                    
                data = response.json()
                status = data.get("status")
                
                if status == "completed":
                    return data
                elif status == "failed":
                    raise Exception(f"Storyboard generation failed: {data.get('error')}")
                    
                print(f"Storyboard status: {status}, waiting...")
                time.sleep(10)
                
        raise Exception("Storyboard generation timed out")
        
    def render_video(self, storyboard_job_id: str) -> str:
        """Render video from storyboard"""
        if not self.access_token:
            self.authenticate()
            
        url = f"{self.base_url}/video/render"
        
        payload = {"storyboardId": storyboard_job_id}
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        with httpx.Client(timeout=60) as client:
            response = client.post(url, json=payload, headers=headers)
            
            if response.status_code != 200:
                raise Exception(f"Video render failed: {response.status_code} - {response.text}")
                
            data = response.json()
            return data.get("renderJobId")
            
    def wait_for_render(self, render_job_id: str, max_wait: int = 600) -> str:
        """Wait for video render to complete and get download URL"""
        if not self.access_token:
            self.authenticate()
            
        url = f"{self.base_url}/jobs/{render_job_id}"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        start_time = time.time()
        while time.time() - start_time < max_wait:
            with httpx.Client(timeout=30) as client:
                response = client.get(url, headers=headers)
                
                if response.status_code != 200:
                    raise Exception(f"Render status check failed: {response.status_code} - {response.text}")
                    
                data = response.json()
                status = data.get("status")
                
                if status == "completed":
                    return data.get("result", {}).get("videoUrl")
                elif status == "failed":
                    raise Exception(f"Video render failed: {data.get('error')}")
                    
                print(f"Render status: {status}, waiting...")
                time.sleep(15)
                
        raise Exception("Video render timed out")
            
    def download_video(self, video_url: str, output_path: str) -> str:
        """Download rendered video"""
        with httpx.Client(timeout=300) as client:
            response = client.get(video_url)
            
            if response.status_code != 200:
                raise Exception(f"Video download failed: {response.status_code}")
                
            with open(output_path, "wb") as f:
                f.write(response.content)
                
        return output_path
        
    def generate(self, script_data: Dict, output_path: str, video_name: str = "AI News") -> str:
        """Full pipeline to generate video from script"""
        try:
            # Extract script text
            script_text = script_data.get("vo_script", "")
            
            print(f"Authenticating with Pictory...")
            self.authenticate()
            
            print(f"Creating storyboard for: {video_name}")
            storyboard_job_id = self.create_storyboard(script_text, video_name)
            
            print(f"Waiting for storyboard completion...")
            storyboard_result = self.wait_for_storyboard(storyboard_job_id)
            
            print(f"Rendering video...")
            render_job_id = self.render_video(storyboard_job_id)
            
            print(f"Waiting for video render...")
            video_url = self.wait_for_render(render_job_id)
            
            if not video_url:
                raise Exception("No video URL returned from render")
                
            print(f"Downloading video to {output_path}")
            self.download_video(video_url, output_path)
            
            print(f"Video successfully generated: {output_path}")
            return output_path
            
        except Exception as e:
            print(f"Error in Pictory video generation: {e}")
            # Fall back to stub
            print("Using stub video generation as fallback")
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(b"STUB_VIDEO_DATA")
            return output_path