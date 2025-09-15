"""
Enhanced Shotstack integration combining TimelineSpec compatibility with professional templates
Merges existing driver with advanced news video features
"""
import os
import time
import json
import httpx
from typing import Dict, List, Optional, Union

SHOTSTACK_HOST = os.getenv("SHOTSTACK_HOST", "https://api.shotstack.io/v1")
SHOTSTACK_API_KEY = os.getenv("SHOTSTACK_API_KEY")

class ShotstackEnhanced:
    def __init__(self):
        if not SHOTSTACK_API_KEY:
            raise RuntimeError("SHOTSTACK_API_KEY not set")
        self.api_key = SHOTSTACK_API_KEY
        self.base_url = SHOTSTACK_HOST
        
    def render_from_timeline_spec(self, spec: dict, out_path: str):
        """
        Render from existing TimelineSpec format (backward compatible)
        Expected spec: {'fps':30, 'size':[1920,1080], 'tracks':{'audioVO':[], 'video':[], 'overlays':[], 'captions':[]}}
        """
        payload = self._timeline_spec_to_shotstack(spec)
        render_id = self._submit_render(payload)
        result = self._poll_render(render_id)
        if result.get("status") not in ("done", "completed"):
            raise RuntimeError(f"Render failed: {result}")
        return self._download_result(result, out_path)
    
    def render_news_video(self,
                         title: str,
                         segments: List[Dict],
                         voiceover_url: str,
                         duration: float,
                         output_path: str,
                         style: str = "professional") -> str:
        """
        High-level API for professional news videos
        segments: [{'chapter_title': str, 'duration': float, 'broll_url': str, 'text': str}]
        style: 'professional', 'minimal', 'dynamic'
        """
        timeline = self._create_news_timeline(title, segments, voiceover_url, duration, style)
        payload = {
            "timeline": timeline,
            "output": {
                "format": "mp4",
                "resolution": "hd",  # 1280x720, use 'fhd' for 1920x1080
                "fps": 30
            }
        }
        
        render_id = self._submit_render(payload)
        result = self._poll_render(render_id)
        if result.get("status") not in ("done", "completed"):
            raise RuntimeError(f"Render failed: {result}")
        return self._download_result(result, output_path)
    
    def _timeline_spec_to_shotstack(self, spec: dict) -> dict:
        """Convert TimelineSpec format to Shotstack JSON"""
        width, height = spec.get("size", [1920, 1080])
        fps = spec.get("fps", 30)
        
        # Build tracks
        tracks = []
        
        # Audio track (voiceover + background music)
        audio_clips = []
        for audio in spec.get("tracks", {}).get("audioVO", []):
            src = audio.get("src")
            if src:
                audio_clips.append({
                    "asset": {"type": "audio", "src": src},
                    "start": float(audio.get("tStart", 0)),
                    "length": None  # Auto-detect
                })
        
        # Add background music if specified
        if spec.get("backgroundMusic"):
            audio_clips.append({
                "asset": {
                    "type": "audio",
                    "src": spec["backgroundMusic"],
                    "volume": 0.15
                },
                "start": 0,
                "length": None
            })
        
        if audio_clips:
            tracks.append({"clips": audio_clips})
        
        # Video/Image track
        video_clips = []
        for item in spec.get("tracks", {}).get("video", []):
            start = float(item.get("tStart", 0))
            length = max(0.01, float(item.get("tEnd", start) - start))
            src = item.get("src")
            
            if src:
                # Determine asset type
                is_video = src.lower().endswith((".mp4", ".mov", ".m4v", ".webm"))
                asset = {"type": "video" if is_video else "image", "src": src}
                
                # Note: Ken Burns effect not directly supported on images
                # Will use transitions for visual interest instead
                
                clip = {
                    "asset": asset,
                    "start": start,
                    "length": length,
                    "fit": item.get("fit", "crop"),
                    "scale": item.get("scale", 1.0)
                }
                
                # Add transitions
                if item.get("transition"):
                    clip["transition"] = {
                        "in": item.get("transition", "fade"),
                        "out": "fade"
                    }
                
                video_clips.append(clip)
        
        if video_clips:
            tracks.append({"clips": video_clips})
        
        # Text overlays and captions
        text_clips = []
        
        # Process overlays (lower thirds, titles)
        for overlay in spec.get("tracks", {}).get("overlays", []):
            text = overlay.get("text", "")
            start = float(overlay.get("tStart", 0))
            length = max(0.01, float(overlay.get("tEnd", start) - start))
            
            # Support HTML overlays for professional styling
            if overlay.get("html"):
                text_clips.append({
                    "asset": {
                        "type": "html",
                        "html": overlay["html"],
                        "width": overlay.get("width", 600),
                        "height": overlay.get("height", 150)
                    },
                    "start": start,
                    "length": length,
                    "position": overlay.get("position", "bottomLeft"),
                    "transition": {"in": "slideRight", "out": "fade"}
                })
            else:
                # Simple title
                text_clips.append({
                    "asset": {
                        "type": "title",
                        "text": text,
                        "style": overlay.get("style", "minimal"),
                        "size": overlay.get("size", "medium"),
                        "color": overlay.get("color", "#ffffff")
                    },
                    "start": start,
                    "length": length,
                    "position": overlay.get("position", "bottom")
                })
        
        # Process captions
        for caption in spec.get("tracks", {}).get("captions", []):
            text = caption.get("text", "")
            start = float(caption.get("tStart", 0))
            length = max(0.01, float(caption.get("tEnd", start) - start))
            
            text_clips.append({
                "asset": {
                    "type": "title",
                    "text": text,
                    "style": "minimal",
                    "size": "small",
                    "color": "#ffffff",
                    "background": caption.get("background", "#000000"),
                    "backgroundOpacity": 0.7
                },
                "start": start,
                "length": length,
                "position": "bottom"
            })
        
        if text_clips:
            tracks.append({"clips": text_clips})
        
        return {
            "timeline": {
                "background": spec.get("background", "#000000"),
                "tracks": tracks
            },
            "output": {
                "format": "mp4",
                "resolution": "1080" if height >= 1080 else "hd",  # hd = 1280x720, 1080 = 1920x1080
                "fps": fps
            }
        }
    
    def _create_news_timeline(self, title: str, segments: List[Dict], 
                             voiceover_url: str, duration: float, 
                             style: str) -> dict:
        """Create professional news video timeline"""
        tracks = []
        
        # Track 1: Voiceover
        tracks.append({
            "clips": [{
                "asset": {"type": "audio", "src": voiceover_url},
                "start": 0,
                "length": duration
            }]
        })
        
        # Track 2: Background music (optional)
        # Note: Removed background music due to 403 error from Shotstack's S3 bucket
        # Could add your own background music URL here if needed
        
        # Track 3: B-roll videos/images
        video_clips = []
        current_time = 3  # Start after title card
        
        for segment in segments:
            if segment.get("broll_url"):
                is_video = segment["broll_url"].lower().endswith((".mp4", ".mov"))
                asset = {
                    "type": "video" if is_video else "image",
                    "src": segment["broll_url"]
                }
                
                # Note: Shotstack doesn't support effects on images directly
                # We'll use transitions instead for visual interest
                
                video_clips.append({
                    "asset": asset,
                    "start": current_time,
                    "length": segment["duration"],
                    "transition": {"in": "fade", "out": "fade"},
                    "fit": "crop",
                    "scale": 1.2 if style == "professional" else 1.0
                })
            else:
                # Fallback gradient background
                video_clips.append({
                    "asset": {"type": "color", "color": "#1a1a2e"},
                    "start": current_time,
                    "length": segment["duration"]
                })
            
            current_time += segment["duration"]
        
        tracks.append({"clips": video_clips})
        
        # Track 4: Text overlays
        text_clips = []
        
        # Opening title card
        if style in ["professional", "dynamic"]:
            title_html = self._create_title_card_html(title, style)
            text_clips.append({
                "asset": {
                    "type": "html",
                    "html": title_html,
                    "width": 1280,
                    "height": 720
                },
                "start": 0,
                "length": 3,
                "transition": {"out": "slideLeft"}
            })
        
        # Lower thirds for segments
        current_time = 3
        for segment in segments:
            if segment.get("chapter_title"):
                if style == "minimal":
                    # Simple text overlay
                    text_clips.append({
                        "asset": {
                            "type": "title",
                            "text": segment["chapter_title"],
                            "style": "minimal",
                            "size": "medium",
                            "color": "#ffffff"
                        },
                        "start": current_time,
                        "length": min(4, segment["duration"]),
                        "position": "bottom"
                    })
                else:
                    # HTML lower third
                    lower_third_html = self._create_lower_third_html(
                        segment["chapter_title"], style
                    )
                    text_clips.append({
                        "asset": {
                            "type": "html",
                            "html": lower_third_html,
                            "width": 600,
                            "height": 150,
                            "position": "bottomLeft"
                        },
                        "start": current_time,
                        "length": min(4, segment["duration"]),
                        "transition": {"in": "slideRight", "out": "fade"}
                    })
            
            current_time += segment["duration"]
        
        if text_clips:
            tracks.append({"clips": text_clips})
        
        return {
            "tracks": tracks,
            "background": "#000000"
        }
    
    def _create_title_card_html(self, title: str, style: str) -> str:
        """Generate HTML for title card"""
        if style == "dynamic":
            gradient = "linear-gradient(135deg, #667eea 0%, #764ba2 100%)"
            font_size = "72px"
        else:  # professional
            gradient = "linear-gradient(135deg, #1e3c72 0%, #2a5298 100%)"
            font_size = "64px"
        
        return f'''
        <div style="
            width: 1280px;
            height: 720px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: {gradient};
        ">
            <div style="text-align: center;">
                <h1 style="
                    color: white;
                    font-family: 'Montserrat', sans-serif;
                    font-size: {font_size};
                    font-weight: 800;
                    text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
                    margin: 0;
                ">{title}</h1>
                <p style="
                    color: white;
                    font-family: 'Open Sans', sans-serif;
                    font-size: 32px;
                    margin-top: 20px;
                    opacity: 0.9;
                ">AI News Briefing</p>
            </div>
        </div>
        '''
    
    def _create_lower_third_html(self, text: str, style: str) -> str:
        """Generate HTML for lower third overlay"""
        if style == "dynamic":
            border_color = "#667eea"
            bg_opacity = "0.9"
        else:  # professional
            border_color = "#2a5298"
            bg_opacity = "0.8"
        
        return f'''
        <div style="
            position: absolute;
            bottom: 100px;
            left: 50px;
            background: rgba(0,0,0,{bg_opacity});
            padding: 20px 30px;
            border-left: 4px solid {border_color};
            backdrop-filter: blur(10px);
        ">
            <h2 style="
                color: white;
                font-family: 'Montserrat', sans-serif;
                font-size: 36px;
                margin: 0;
                font-weight: 600;
            ">{text}</h2>
        </div>
        '''
    
    def _submit_render(self, payload: dict) -> str:
        """Submit render job to Shotstack"""
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        with httpx.Client(timeout=60) as client:
            response = client.post(
                f"{self.base_url}/render",
                content=json.dumps(payload),
                headers=headers
            )
            if response.status_code >= 300:
                raise RuntimeError(f"Submit failed: {response.status_code} {response.text}")
            return response.json().get("response", {}).get("id")
    
    def _poll_render(self, render_id: str, poll_interval: int = 5, timeout: int = 120) -> dict:
        """Poll render status until complete"""
        headers = {"x-api-key": self.api_key}
        start_time = time.time()
        
        with httpx.Client(timeout=60) as client:
            while time.time() - start_time < timeout:
                response = client.get(
                    f"{self.base_url}/render/{render_id}",
                    headers=headers
                )
                if response.status_code >= 300:
                    raise RuntimeError(f"Status check failed: {response.status_code}")
                
                data = response.json().get("response", {})
                status = data.get("status")
                
                if status == "done":
                    # For done status, the URL should be available
                    return data
                elif status in ("failed", "cancelled"):
                    return data
                
                # Show progress
                progress = data.get("renderProgress", 0)
                print(f"Render progress: {progress}% - Status: {status}")
                time.sleep(poll_interval)
        
        raise RuntimeError("Render polling timeout")
    
    def _download_result(self, data: dict, output_path: str) -> str:
        """Download rendered video"""
        url = data.get("url") or (data.get("output", {}) or {}).get("url")
        if not url:
            raise RuntimeError("No output URL in render response")
        
        with httpx.Client(timeout=600) as client:
            with client.stream("GET", url) as response:
                response.raise_for_status()
                with open(output_path, "wb") as f:
                    for chunk in response.iter_bytes():
                        f.write(chunk)
        
        return output_path

# Convenience functions for backward compatibility
def render_with_shotstack(spec: dict, out_path: str):
    """Drop-in replacement for existing driver"""
    api = ShotstackEnhanced()
    return api.render_from_timeline_spec(spec, out_path)

def create_news_video(title: str, segments: List[Dict], 
                     voiceover_url: str, duration: float,
                     output_path: str, style: str = "professional") -> str:
    """High-level API for news videos"""
    api = ShotstackEnhanced()
    return api.render_news_video(
        title, segments, voiceover_url, 
        duration, output_path, style
    )