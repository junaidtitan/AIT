"""
Shotstack API integration for professional video generation
More control and cost-effective than Pictory for templated content
"""
import os
import time
import httpx
from typing import Dict, List, Optional

class ShotstackAPI:
    def __init__(self):
        self.api_key = os.getenv("SHOTSTACK_API_KEY")
        self.base_url = "https://api.shotstack.io/stage"  # Use 'v1' for production
        
    def create_news_video(self, 
                          title: str,
                          segments: List[Dict],
                          voiceover_url: str,
                          duration: float) -> str:
        """
        Create professional news video with:
        - Title cards
        - Lower thirds
        - B-roll with Ken Burns effect
        - Background music
        - Transitions
        """
        
        timeline = {
            "tracks": [
                # Track 1: Voiceover (bottom layer)
                {
                    "clips": [{
                        "asset": {
                            "type": "audio",
                            "src": voiceover_url
                        },
                        "start": 0,
                        "length": duration
                    }]
                },
                # Track 2: Background music
                {
                    "clips": [{
                        "asset": {
                            "type": "audio",
                            "src": "https://shotstack-assets.s3.amazonaws.com/music/news.mp3",
                            "volume": 0.15
                        },
                        "start": 0,
                        "length": duration
                    }]
                },
                # Track 3: B-roll videos/images
                self._create_broll_track(segments),
                # Track 4: Text overlays
                self._create_text_track(title, segments)
            ],
            "background": "#000000"
        }
        
        payload = {
            "timeline": timeline,
            "output": {
                "format": "mp4",
                "resolution": "hd",  # 1280x720, use 'fhd' for 1920x1080
                "fps": 30
            }
        }
        
        # Submit render
        headers = {"x-api-key": self.api_key}
        with httpx.Client() as client:
            response = client.post(
                f"{self.base_url}/render",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            render_id = response.json()["response"]["id"]
            
        return self._wait_for_render(render_id)
    
    def _create_broll_track(self, segments: List[Dict]) -> Dict:
        """Create track with B-roll footage"""
        clips = []
        current_time = 0
        
        for segment in segments:
            # Use provided B-roll or fallback to color background
            if segment.get("broll_url"):
                asset = {
                    "type": "video" if segment["broll_url"].endswith(".mp4") else "image",
                    "src": segment["broll_url"]
                }
                # Add Ken Burns effect to images
                if asset["type"] == "image":
                    asset["effect"] = "zoomIn"
            else:
                # Gradient background as fallback
                asset = {
                    "type": "color",
                    "color": "#1a1a2e"
                }
            
            clips.append({
                "asset": asset,
                "start": current_time,
                "length": segment["duration"],
                "transition": {
                    "in": "fade",
                    "out": "fade"
                },
                "fit": "crop",
                "scale": 1.2  # Slight zoom for professional look
            })
            current_time += segment["duration"]
            
        return {"clips": clips}
    
    def _create_text_track(self, title: str, segments: List[Dict]) -> Dict:
        """Create track with title cards and lower thirds"""
        clips = []
        
        # Opening title card
        clips.append({
            "asset": {
                "type": "html",
                "html": f'''
                <div style="
                    width: 1280px;
                    height: 720px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                ">
                    <div style="text-align: center;">
                        <h1 style="
                            color: white;
                            font-family: 'Montserrat', sans-serif;
                            font-size: 72px;
                            font-weight: 800;
                            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
                        ">{title}</h1>
                        <p style="
                            color: white;
                            font-family: 'Open Sans', sans-serif;
                            font-size: 32px;
                            margin-top: 20px;
                        ">AI News Briefing</p>
                    </div>
                </div>
                ''',
                "width": 1280,
                "height": 720
            },
            "start": 0,
            "length": 3,
            "transition": {"out": "slideLeft"}
        })
        
        # Lower thirds for each segment
        current_time = 3
        for i, segment in enumerate(segments):
            if segment.get("chapter_title"):
                clips.append({
                    "asset": {
                        "type": "html",
                        "html": f'''
                        <div style="
                            position: absolute;
                            bottom: 100px;
                            left: 50px;
                            background: rgba(0,0,0,0.8);
                            padding: 20px 30px;
                            border-left: 4px solid #667eea;
                        ">
                            <h2 style="
                                color: white;
                                font-family: 'Montserrat', sans-serif;
                                font-size: 36px;
                                margin: 0;
                            ">{segment["chapter_title"]}</h2>
                        </div>
                        ''',
                        "width": 600,
                        "height": 150,
                        "position": "bottomLeft"
                    },
                    "start": current_time,
                    "length": 4,
                    "transition": {"in": "slideRight", "out": "fade"}
                })
            current_time += segment["duration"]
            
        return {"clips": clips}
    
    def _wait_for_render(self, render_id: str, timeout: int = 300) -> str:
        """Poll for render completion"""
        headers = {"x-api-key": self.api_key}
        start_time = time.time()
        
        with httpx.Client() as client:
            while time.time() - start_time < timeout:
                response = client.get(
                    f"{self.base_url}/render/{render_id}",
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()["response"]
                
                status = data["status"]
                if status == "done":
                    return data["url"]
                elif status == "failed":
                    raise Exception(f"Render failed: {data.get('error')}")
                
                print(f"Render status: {status}, progress: {data.get('renderProgress', 0)}%")
                time.sleep(5)
                
        raise Exception("Render timeout")

# Example usage:
if __name__ == "__main__":
    api = ShotstackAPI()
    
    segments = [
        {
            "chapter_title": "OpenAI GPT-5 Launch",
            "duration": 30,
            "broll_url": "https://example.com/tech-visual.jpg"
        },
        {
            "chapter_title": "Market Impact",
            "duration": 25,
            "broll_url": "https://example.com/charts.mp4"
        }
    ]
    
    video_url = api.create_news_video(
        title="Today in AI",
        segments=segments,
        voiceover_url="https://example.com/voiceover.mp3",
        duration=60
    )
    
    print(f"Video ready: {video_url}")