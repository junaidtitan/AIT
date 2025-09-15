"""
Video Renderer Selector - Smart routing between Shotstack and Pictory
Uses Shotstack for cost-effective templated content, Pictory for complex needs
"""
import os
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class VideoRendererSelector:
    def __init__(self):
        self.shotstack_enabled = bool(os.getenv("SHOTSTACK_API_KEY"))
        self.pictory_enabled = bool(os.getenv("PICTORY_CLIENT_ID"))
        
        if not self.shotstack_enabled and not self.pictory_enabled:
            raise RuntimeError("No video rendering service configured. Set SHOTSTACK_API_KEY or PICTORY_CLIENT_ID")
    
    def render_video(self,
                    script: str,
                    title: str,
                    segments: List[Dict],
                    voiceover_url: str,
                    output_path: str,
                    prefer_shotstack: bool = True,
                    style: str = "professional") -> str:
        """
        Intelligently route video rendering to the best service
        
        Args:
            script: Full script text
            title: Video title
            segments: List of segment dictionaries with chapter_title, duration, broll_url
            voiceover_url: URL to voiceover audio
            output_path: Where to save the final video
            prefer_shotstack: Use Shotstack when possible (cost-effective)
            style: Video style (professional, minimal, dynamic)
        
        Returns:
            Path to rendered video
        """
        
        # Determine which renderer to use
        use_shotstack = self._should_use_shotstack(
            script, segments, prefer_shotstack
        )
        
        if use_shotstack and self.shotstack_enabled:
            try:
                logger.info("Using Shotstack for video rendering (cost-effective)")
                return self._render_with_shotstack(
                    title, segments, voiceover_url, output_path, style
                )
            except Exception as e:
                logger.warning(f"Shotstack render failed: {e}, falling back to Pictory")
                if self.pictory_enabled:
                    return self._render_with_pictory(script, title, output_path)
                raise
        
        elif self.pictory_enabled:
            logger.info("Using Pictory for video rendering (advanced B-roll)")
            return self._render_with_pictory(script, title, output_path)
        
        else:
            raise RuntimeError("No suitable video renderer available")
    
    def _should_use_shotstack(self, script: str, segments: List[Dict], 
                             prefer_shotstack: bool) -> bool:
        """
        Determine if Shotstack is suitable for this video
        
        Shotstack is best for:
        - Videos under 10 minutes
        - Content with provided B-roll URLs
        - Templated news/briefing formats
        - Cost-conscious production
        
        Pictory is better for:
        - Long-form content (>10 min)
        - Content needing automatic B-roll discovery
        - Complex scene matching
        """
        if not prefer_shotstack:
            return False
        
        # Check video duration
        word_count = len(script.split())
        estimated_minutes = word_count / 150  # 150 words per minute
        
        if estimated_minutes > 10:
            logger.info(f"Video too long for Shotstack ({estimated_minutes:.1f} min)")
            return False
        
        # Check if we have B-roll assets
        has_broll = sum(1 for s in segments if s.get("broll_url")) > len(segments) * 0.5
        
        if not has_broll:
            logger.info("Insufficient B-roll assets for Shotstack")
            return False
        
        return True
    
    def _render_with_shotstack(self, title: str, segments: List[Dict],
                              voiceover_url: str, output_path: str,
                              style: str) -> str:
        """Render using Shotstack API"""
        from .shotstack_enhanced import ShotstackEnhanced
        
        # Calculate total duration from segments
        total_duration = sum(s.get("duration", 30) for s in segments) + 3  # +3 for title card
        
        api = ShotstackEnhanced()
        return api.render_news_video(
            title=title,
            segments=segments,
            voiceover_url=voiceover_url,
            duration=total_duration,
            output_path=output_path,
            style=style
        )
    
    def _render_with_pictory(self, script: str, title: str, output_path: str) -> str:
        """Render using Pictory API"""
        from .pictory_api import PictoryAPI
        import time
        
        api = PictoryAPI()
        
        # Authenticate
        api.authenticate()
        
        # Create storyboard
        video_name = f"{title} - {datetime.now().strftime('%B %d, %Y')}"
        storyboard_id = api.create_storyboard(script, video_name)
        
        # Wait for storyboard
        for _ in range(60):
            status_data = api.check_job_status(storyboard_id)
            if status_data.get("data", {}).get("status") == "completed":
                break
            time.sleep(10)
        else:
            raise RuntimeError("Storyboard generation timed out")
        
        # Render video
        render_id = api.render_video(storyboard_id)
        
        # Wait for render
        for _ in range(180):
            status_data = api.check_job_status(render_id)
            if status_data.get("data", {}).get("status") == "completed":
                video_url = status_data.get("data", {}).get("videoURL")
                if video_url:
                    api.download_video(video_url, output_path)
                    return output_path
                break
            time.sleep(10)
        
        raise RuntimeError("Video render timed out or failed")
    
    def render_from_timeline_spec(self, spec: dict, output_path: str,
                                 prefer_shotstack: bool = True) -> str:
        """
        Render from TimelineSpec format (backward compatible)
        
        Args:
            spec: TimelineSpec dictionary
            output_path: Output file path
            prefer_shotstack: Try Shotstack first if available
        
        Returns:
            Path to rendered video
        """
        if prefer_shotstack and self.shotstack_enabled:
            try:
                from .shotstack_enhanced import render_with_shotstack
                return render_with_shotstack(spec, output_path)
            except Exception as e:
                logger.warning(f"Shotstack failed: {e}, trying Pictory")
        
        if self.pictory_enabled:
            # Convert TimelineSpec to script for Pictory
            script = self._timeline_spec_to_script(spec)
            return self._render_with_pictory(
                script, "AI News Briefing", output_path
            )
        
        raise RuntimeError("No renderer available")
    
    def _timeline_spec_to_script(self, spec: dict) -> str:
        """Convert TimelineSpec to script text for Pictory"""
        # Extract text from overlays and captions
        script_parts = []
        
        for overlay in spec.get("tracks", {}).get("overlays", []):
            if overlay.get("text"):
                script_parts.append(overlay["text"])
        
        for caption in spec.get("tracks", {}).get("captions", []):
            if caption.get("text"):
                script_parts.append(caption["text"])
        
        return " ".join(script_parts) if script_parts else "AI News Briefing"
    
    def get_cost_estimate(self, duration_minutes: float, 
                         use_shotstack: bool) -> Dict[str, float]:
        """
        Estimate rendering costs
        
        Returns:
            Dictionary with cost breakdown
        """
        if use_shotstack:
            # Shotstack: ~$0.024 per minute
            render_cost = duration_minutes * 0.024
            return {
                "service": "Shotstack",
                "render_cost": render_cost,
                "monthly_estimate": render_cost * 30,  # Daily videos
                "notes": "Cost-effective for templated content"
            }
        else:
            # Pictory: Fixed monthly tiers
            if duration_minutes * 30 <= 200:  # 200 min/month
                monthly = 89
            elif duration_minutes * 30 <= 600:
                monthly = 179
            else:
                monthly = 389
            
            return {
                "service": "Pictory",
                "render_cost": monthly / 30,  # Per video
                "monthly_estimate": monthly,
                "notes": "Includes automatic B-roll discovery"
            }

# Example usage
if __name__ == "__main__":
    renderer = VideoRendererSelector()
    
    # Example segments for a news video
    segments = [
        {
            "chapter_title": "OpenAI GPT-5 Launch",
            "duration": 30,
            "broll_url": "https://example.com/tech.jpg",
            "text": "OpenAI announces GPT-5..."
        },
        {
            "chapter_title": "Market Impact", 
            "duration": 25,
            "broll_url": "https://example.com/charts.mp4",
            "text": "The market responds..."
        }
    ]
    
    # Render with intelligent routing
    output = renderer.render_video(
        script="Full news script here...",
        title="Today in AI",
        segments=segments,
        voiceover_url="https://example.com/voiceover.mp3",
        output_path="/tmp/daily_news.mp4",
        prefer_shotstack=True,  # Use cost-effective option when possible
        style="professional"
    )
    
    print(f"Video rendered: {output}")
    
    # Get cost estimate
    cost = renderer.get_cost_estimate(duration_minutes=5, use_shotstack=True)
    print(f"Estimated cost: ${cost['render_cost']:.3f} per video")
    print(f"Monthly: ${cost['monthly_estimate']:.2f}")
