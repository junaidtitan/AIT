#!/usr/bin/env python3
"""
Enhanced Pipeline Integration
Combines shot list generator, enhanced B-roll research, and dynamic timeline builder
"""

import os
import sys
import json
import time
import asyncio
from typing import List, Dict, Optional
from datetime import datetime

# Import all enhanced components
from shot_list_generator import ShotListGenerator
from enhanced_broll_research import EnhancedBrollResearch
from shotstack_dynamic import ShotstackDynamic

class EnhancedVideoProducer:
    """Integrates all enhanced components for professional video production"""
    
    def __init__(self):
        """Initialize all enhanced components"""
        self.shot_generator = ShotListGenerator()
        self.broll_researcher = EnhancedBrollResearch()
        self.timeline_builder = ShotstackDynamic()
    
    def produce_enhanced_video(self, 
                              script: str, 
                              voiceover_url: str,
                              title: str = None,
                              webhook_url: Optional[str] = None) -> Dict:
        """
        Produce enhanced video using the full pipeline
        
        Args:
            script: The voiceover script
            voiceover_url: URL of the voiceover audio
            title: Video title
            webhook_url: Optional webhook for render completion
            
        Returns:
            Dict with render_id and timeline details
        """
        print("\n" + "="*60)
        print("🎬 ENHANCED VIDEO PRODUCTION PIPELINE")
        print("="*60)
        
        # Step 1: Generate detailed shot list
        print("\n[1/5] Generating shot list with Universal B-Roll Template...")
        duration = len(script.split()) / 150 * 60  # Estimate duration
        shot_list = self.shot_generator.generate_shot_list(script, duration)
        
        print(f"  ✓ Generated {len(shot_list)} segments")
        total_shots = sum(len(segment.get('shots', [])) for segment in shot_list)
        print(f"  ✓ Total shots: {total_shots}")
        
        # Step 2: Research B-roll assets
        print("\n[2/5] Researching B-roll assets with multi-layer keywords...")
        enhanced_shot_list = self.broll_researcher.research_sync(shot_list)
        
        assets_found = sum(
            len(shot.get('assets', [])) 
            for segment in enhanced_shot_list 
            for shot in segment.get('shots', [])
        )
        print(f"  ✓ Found {assets_found} assets")
        
        # Step 3: Build dynamic timeline
        print("\n[3/5] Building dynamic timeline with 4-7 second cuts...")
        timeline = self.timeline_builder.build_dynamic_timeline(
            shot_list=enhanced_shot_list,
            voiceover_url=voiceover_url,
            total_duration=duration
        )
        
        clips_count = len(timeline['timeline']['tracks'][0]['clips'])
        print(f"  ✓ Created {clips_count} B-roll clips")
        
        # Add title if provided
        if title:
            timeline['timeline']['tracks'][2]['clips'].insert(0, {
                "asset": {
                    "type": "html",
                    "html": f"""
                    <div style="
                        display: flex;
                        justify-content: center;
                        align-items: center;
                        height: 100%;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        font-family: 'Montserrat', sans-serif;
                        font-size: 72px;
                        font-weight: 800;
                        color: white;
                        text-shadow: 4px 4px 8px rgba(0,0,0,0.3);
                    ">{title}</div>
                    """,
                    "width": 1920,
                    "height": 1080
                },
                "start": 0,
                "length": 2,
                "transition": {"in": "fade", "out": "fade"}
            })
        
        # Step 4: Submit for rendering
        print("\n[4/5] Submitting to Shotstack for rendering...")
        try:
            render_id = self.timeline_builder.render_video(timeline, webhook_url)
            print(f"  ✓ Render ID: {render_id}")
            
            # Step 5: Monitor rendering (optional)
            print("\n[5/5] Monitoring render progress...")
            print("  This will take 1-2 minutes...")
            
            return {
                'render_id': render_id,
                'timeline': timeline,
                'shot_list': enhanced_shot_list,
                'duration': duration,
                'clips_count': clips_count,
                'assets_found': assets_found
            }
            
        except Exception as e:
            print(f"  ❌ Render submission failed: {e}")
            return {
                'error': str(e),
                'timeline': timeline,
                'shot_list': enhanced_shot_list
            }
    
    def wait_for_completion(self, render_id: str, timeout: int = 120) -> str:
        """
        Wait for render to complete and return video URL
        
        Args:
            render_id: The render job ID
            timeout: Maximum wait time in seconds
            
        Returns:
            URL of the completed video
        """
        try:
            video_url = self.timeline_builder.wait_for_render(render_id, timeout)
            print(f"\n✅ Video ready: {video_url}")
            return video_url
        except Exception as e:
            print(f"\n❌ Render failed: {e}")
            raise


def run_enhanced_test():
    """Test the enhanced pipeline with sample content"""
    
    # Sample AI news script
    test_script = """
    Breaking developments in artificial intelligence are reshaping the technology landscape.
    
    OpenAI's latest GPT model demonstrates unprecedented reasoning capabilities, solving complex 
    mathematical problems that previously required human expertise. Early testing shows a 40 percent 
    improvement in accuracy across scientific domains.
    
    Meanwhile, Google DeepMind achieves a breakthrough in quantum computing simulation. Their new 
    algorithm can model quantum systems with 100 qubits, opening doors to revolutionary drug 
    discovery and materials science applications.
    
    In the open-source community, Meta releases powerful vision models that rival proprietary 
    alternatives. These models enable real-time video analysis on consumer hardware, democratizing 
    access to advanced AI capabilities.
    
    Industry leaders predict these advances will accelerate AI adoption across enterprises, with 
    automation becoming mainstream by 2025. The convergence of improved models, reduced costs, 
    and broader accessibility marks a pivotal moment in AI evolution.
    """
    
    # Test voiceover URL (placeholder)
    voiceover_url = "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"
    
    # Initialize producer
    producer = EnhancedVideoProducer()
    
    # Produce enhanced video
    result = producer.produce_enhanced_video(
        script=test_script,
        voiceover_url=voiceover_url,
        title="AI News Today",
        webhook_url=None
    )
    
    # Print summary
    print("\n" + "="*60)
    print("📊 PRODUCTION SUMMARY")
    print("="*60)
    
    if 'render_id' in result:
        print(f"✓ Render ID: {result['render_id']}")
        print(f"✓ Duration: {result['duration']:.1f} seconds")
        print(f"✓ Total clips: {result['clips_count']}")
        print(f"✓ Assets found: {result['assets_found']}")
        
        # Save timeline for debugging
        timeline_path = f"enhanced_timeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(timeline_path, 'w') as f:
            json.dump(result['timeline'], f, indent=2)
        print(f"✓ Timeline saved: {timeline_path}")
        
        # Wait for completion (optional)
        if input("\nWait for render completion? (y/n): ").lower() == 'y':
            try:
                video_url = producer.wait_for_completion(result['render_id'])
                print(f"\n🎬 Final video: {video_url}")
            except Exception as e:
                print(f"\n⚠ Could not get final video: {e}")
    else:
        print(f"❌ Production failed: {result.get('error', 'Unknown error')}")
        
        # Still save timeline for debugging
        if 'timeline' in result:
            timeline_path = f"failed_timeline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(timeline_path, 'w') as f:
                json.dump(result['timeline'], f, indent=2)
            print(f"  Timeline saved for debugging: {timeline_path}")


if __name__ == "__main__":
    # Check for required API keys
    required_keys = ['SHOTSTACK_API_KEY', 'PEXELS_API_KEY']
    missing_keys = [k for k in required_keys if not os.environ.get(k)]
    
    if missing_keys:
        print(f"⚠ Warning: Missing API keys: {', '.join(missing_keys)}")
        print("  Some features may be limited")
    
    # Run test
    run_enhanced_test()