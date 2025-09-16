#!/usr/bin/env python3
"""
Shotstack Dynamic Timeline Builder
Creates fast-paced videos with 4-7 second cuts and professional transitions
"""

import os
import sys
import json
import time
import requests
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import random

class ShotstackDynamic:
    """Dynamic timeline builder for Shotstack with enhanced pacing"""
    
    def __init__(self):
        """Initialize Shotstack Dynamic with API configuration"""
        self.api_key = os.environ.get('SHOTSTACK_API_KEY')
        if not self.api_key:
            raise ValueError("SHOTSTACK_API_KEY environment variable not set")
        
        # Use production API to remove watermark
        # Note: Production endpoint requires a paid account
        self.api_url = "https://api.shotstack.io/v1"
        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        # Professional transitions for different styles (Shotstack-supported)
        self.transitions = {
            'Cinematic': ['fade', 'wipeLeft', 'wipeRight', 'slideLeft'],
            'Abstract/Futuristic': ['zoom', 'carouselLeft', 'carouselRight', 'shuffleTopRight'],
            'Documentary/Stock': ['fade', 'fadeSlow', 'slideUp', 'slideDown'],
            'Graphic/Text Overlay': ['fade', 'slideLeft', 'slideRight']
        }
        
        # Effects for different styles (using Shotstack-supported effects)
        self.effects = {
            'Cinematic': ['zoomIn', 'zoomOut', 'slideLeft', 'slideRight'],
            'Abstract/Futuristic': ['zoomIn', 'zoomOut', 'slideUp', 'slideDown'],
            'Documentary/Stock': ['zoomInSlow', 'zoomOutSlow'],  # Ken Burns-like effect
            'Graphic/Text Overlay': None
        }
    
    def build_dynamic_timeline(self, 
                              shot_list: List[Dict], 
                              voiceover_url: str,
                              total_duration: float) -> Dict:
        """
        Build a dynamic timeline with fast-paced cuts
        
        Args:
            shot_list: List of shot segments with assets and timing
            voiceover_url: URL of the voiceover audio
            total_duration: Total duration of the video
            
        Returns:
            Shotstack timeline specification
        """
        # Initialize tracks
        broll_clips = []
        text_clips = []
        graphics_clips = []
        
        current_time = 0
        
        for segment_idx, segment in enumerate(shot_list):
            shots = segment.get('shots', [])
            segment_duration = segment.get('duration', 6)
            
            if not shots:
                continue
            
            # Calculate duration per shot (4-7 seconds ideal)
            shot_duration = min(7, max(4, segment_duration / len(shots)))
            
            for shot_idx, shot in enumerate(shots):
                # Get best asset for this shot
                assets = shot.get('assets', [])
                if not assets:
                    continue
                
                asset = assets[0]  # Use best ranked asset
                asset_url = asset.get('cached_url', asset.get('url'))
                
                if not asset_url:
                    continue
                
                # Create B-roll clip
                clip = self._create_dynamic_clip(
                    asset_url=asset_url,
                    asset_type=asset.get('type', 'image'),
                    start_time=current_time,
                    duration=shot_duration,
                    style=shot.get('style', 'Documentary/Stock'),
                    shot_index=shot_idx,
                    segment_index=segment_idx
                )
                
                broll_clips.append(clip)
                
                # Add text overlay if needed
                if shot.get('text_overlay'):
                    text_clip = self._create_text_overlay(
                        text=shot['text_overlay'],
                        start_time=current_time,
                        duration=shot_duration,
                        style=shot.get('style')
                    )
                    text_clips.append(text_clip)
                
                # Add lower third for key information
                if segment_idx == 0 and shot_idx == 0:
                    # Add title card at beginning
                    title_clip = self._create_title_card(
                        title="TODAY IN AI",
                        subtitle=datetime.now().strftime("%B %d, %Y"),
                        start_time=0,
                        duration=3
                    )
                    graphics_clips.append(title_clip)
                
                current_time += shot_duration
        
        # Add end card
        end_card = self._create_end_card(
            start_time=current_time,
            duration=3
        )
        graphics_clips.append(end_card)
        
        # Build timeline with only non-empty tracks
        tracks = []
        
        # Add B-roll track (primary content) - must have clips
        if broll_clips:
            tracks.append({"clips": broll_clips})
        
        # Add text overlay track only if it has clips
        if text_clips and len(text_clips) > 0:
            tracks.append({"clips": text_clips})
        
        # Add graphics track only if it has clips  
        if graphics_clips and len(graphics_clips) > 0:
            tracks.append({"clips": graphics_clips})
        
        # Ensure at least one track exists
        if not tracks:
            # Create a placeholder clip if no content
            placeholder_clip = {
                "asset": {
                    "type": "html",
                    "html": "<div style='background: #000; width: 100%; height: 100%;'></div>",
                    "width": 1920,
                    "height": 1080
                },
                "start": 0,
                "length": total_duration
            }
            tracks = [{"clips": [placeholder_clip]}]
        
        timeline = {
            "timeline": {
                "soundtrack": {
                    "src": voiceover_url,
                    "effect": "fadeInFadeOut"
                },
                "background": "#000000",
                "tracks": tracks
            },
            "output": {
                "format": "mp4",
                "resolution": "hd",
                "aspectRatio": "16:9",
                "fps": 30,
                "scaleTo": "preview",
                "quality": "high"
            }
        }
        
        return timeline
    
    def _create_dynamic_clip(self, asset_url: str, asset_type: str, start_time: float,
                            duration: float, style: str, shot_index: int, 
                            segment_index: int) -> Dict:
        """Create a dynamic clip with effects and transitions"""
        
        clip = {
            "asset": {
                "type": "video" if asset_type == "video" else "image",
                "src": asset_url
            },
            "start": start_time,
            "length": duration,
            "fit": "crop",  # Changed from "cover" to "crop" for full screen
            "scale": 1,     # Changed from 0 to 1 for full scale
            "position": "center",
            "offset": {
                "x": 0,
                "y": 0
            }
        }
        
        # Add transition based on style
        transitions = self.transitions.get(style, ['fade'])
        if shot_index == 0:
            # First shot of segment gets a fade in
            clip["transition"] = {
                "in": "fade",
                "out": random.choice(transitions)
            }
        else:
            # Other shots get varied transitions
            clip["transition"] = {
                "in": random.choice(transitions),
                "out": random.choice(transitions)
            }
        
        # Add effect based on style
        effects = self.effects.get(style)
        if effects and asset_type == "image":
            clip["effect"] = random.choice(effects)
        
        # Add filter for cinematic style (using Shotstack string filters)
        if style == "Cinematic":
            clip["filter"] = "darken"  # Cinematic darker look
        elif style == "Abstract/Futuristic":
            clip["filter"] = "boost"  # Boosted saturation for futuristic
        
        # Add opacity for abstract style
        if style == "Abstract/Futuristic":
            clip["opacity"] = 0.9  # Slight transparency for layered look
        
        return clip
    
    def _create_text_overlay(self, text: str, start_time: float, 
                           duration: float, style: str) -> Dict:
        """Create a text overlay clip"""
        
        # Style-specific text formatting
        text_styles = {
            'Cinematic': {
                'font': 'Montserrat',
                'size': 'large',
                'color': '#ffffff',
                'background': '#000000aa'
            },
            'Abstract/Futuristic': {
                'font': 'Open Sans',
                'size': 'x-large',
                'color': '#00ffff',
                'background': 'transparent'
            },
            'Documentary/Stock': {
                'font': 'Lato',
                'size': 'medium',
                'color': '#ffffff',
                'background': '#000000cc'
            }
        }
        
        text_style = text_styles.get(style, text_styles['Documentary/Stock'])
        
        return {
            "asset": {
                "type": "html",
                "html": f"""
                <div style="
                    font-family: {text_style['font']}, sans-serif;
                    color: {text_style['color']};
                    font-size: 48px;
                    text-align: center;
                    padding: 20px;
                    background: {text_style['background']};
                    border-radius: 10px;
                    text-shadow: 2px 2px 4px rgba(0,0,0,0.8);
                ">
                    {text}
                </div>
                """,
                "width": 1920,
                "height": 200
            },
            "start": start_time,
            "length": duration,
            "position": "bottom",
            "offset": {
                "x": 0,
                "y": 0.1
            },
            "transition": {
                "in": "slideUp",
                "out": "slideDown"
            }
        }
    
    def _create_title_card(self, title: str, subtitle: str, 
                          start_time: float, duration: float) -> Dict:
        """Create a professional title card"""
        
        return {
            "asset": {
                "type": "html",
                "html": f"""
                <div style="
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    height: 100%;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                ">
                    <h1 style="
                        font-family: 'Montserrat', sans-serif;
                        font-size: 120px;
                        font-weight: 800;
                        color: white;
                        margin: 0;
                        text-shadow: 4px 4px 8px rgba(0,0,0,0.3);
                        letter-spacing: 8px;
                    ">{title}</h1>
                    <p style="
                        font-family: 'Open Sans', sans-serif;
                        font-size: 36px;
                        color: white;
                        margin-top: 20px;
                        opacity: 0.9;
                        letter-spacing: 4px;
                    ">{subtitle}</p>
                </div>
                """,
                "width": 1920,
                "height": 1080
            },
            "start": start_time,
            "length": duration,
            "transition": {
                "in": "fade",
                "out": "fade"
            }
        }
    
    def _create_end_card(self, start_time: float, duration: float) -> Dict:
        """Create an end card with call to action"""
        
        return {
            "asset": {
                "type": "html",
                "html": """
                <div style="
                    display: flex;
                    flex-direction: column;
                    justify-content: center;
                    align-items: center;
                    height: 100%;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                ">
                    <h2 style="
                        font-family: 'Montserrat', sans-serif;
                        font-size: 72px;
                        font-weight: 700;
                        color: white;
                        margin: 0;
                        text-shadow: 3px 3px 6px rgba(0,0,0,0.3);
                    ">Thanks for Watching</h2>
                    <p style="
                        font-family: 'Open Sans', sans-serif;
                        font-size: 36px;
                        color: white;
                        margin-top: 30px;
                        opacity: 0.9;
                    ">Subscribe for Daily AI Updates</p>
                    <div style="
                        margin-top: 40px;
                        padding: 15px 40px;
                        background: white;
                        border-radius: 50px;
                    ">
                        <p style="
                            font-family: 'Open Sans', sans-serif;
                            font-size: 28px;
                            color: #764ba2;
                            margin: 0;
                            font-weight: 600;
                        ">SUBSCRIBE NOW</p>
                    </div>
                </div>
                """,
                "width": 1920,
                "height": 1080
            },
            "start": start_time,
            "length": duration,
            "transition": {
                "in": "fade"
            }
        }
    
    def render_video(self, timeline: Dict, webhook_url: Optional[str] = None) -> str:
        """
        Submit timeline for rendering
        
        Args:
            timeline: Shotstack timeline specification
            webhook_url: Optional webhook for completion notification
            
        Returns:
            Render ID for tracking
        """
        if webhook_url:
            timeline['callback'] = webhook_url
        
        response = requests.post(
            f"{self.api_url}/render",
            headers=self.headers,
            json=timeline
        )
        
        if response.status_code == 201:
            data = response.json()
            return data['response']['id']
        else:
            raise Exception(f"Render submission failed: {response.text}")
    
    def get_render_status(self, render_id: str) -> Dict:
        """Get the status of a render job"""
        response = requests.get(
            f"{self.api_url}/render/{render_id}",
            headers=self.headers
        )
        
        if response.status_code == 200:
            return response.json()['response']
        else:
            raise Exception(f"Status check failed: {response.text}")
    
    def wait_for_render(self, render_id: str, timeout: int = 120) -> str:
        """
        Wait for render to complete
        
        Args:
            render_id: The render job ID
            timeout: Maximum time to wait in seconds
            
        Returns:
            URL of the rendered video
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            status = self.get_render_status(render_id)
            
            if status['status'] == 'done':
                return status['url']
            elif status['status'] == 'failed':
                raise Exception(f"Render failed: {status.get('error', 'Unknown error')}")
            
            # Show progress
            progress = status.get('renderTime', 0)
            print(f"Render progress: {progress}% - Status: {status['status']}")
            
            time.sleep(5)
        
        raise Exception(f"Render timeout after {timeout} seconds")


if __name__ == "__main__":
    # Test the dynamic timeline builder
    test_shot_list = [
        {
            'timestamp': '0:00-0:10',
            'duration': 10,
            'shots': [
                {
                    'style': 'Cinematic',
                    'assets': [
                        {
                            'url': 'https://example.com/video1.mp4',
                            'type': 'video',
                            'cached_url': 'https://storage.googleapis.com/cache/video1.mp4'
                        }
                    ]
                },
                {
                    'style': 'Abstract/Futuristic',
                    'text_overlay': 'Breaking News',
                    'assets': [
                        {
                            'url': 'https://example.com/image1.jpg',
                            'type': 'image'
                        }
                    ]
                }
            ]
        }
    ]
    
    builder = ShotstackDynamic()
    timeline = builder.build_dynamic_timeline(
        shot_list=test_shot_list,
        voiceover_url='https://example.com/voiceover.mp3',
        total_duration=30
    )
    
    print("Dynamic Timeline:")
    print(json.dumps(timeline, indent=2))