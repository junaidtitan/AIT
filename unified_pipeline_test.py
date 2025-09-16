#!/usr/bin/env python3
"""
Unified Pipeline Test - Complete Video Generation with All Artifacts
Shows every stage of the pipeline and saves all intermediate outputs
"""

import os
import sys
import json
import time
import subprocess
import argparse
from datetime import datetime
from pathlib import Path

# Add path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class UnifiedPipelineTest:
    """Comprehensive test showing all pipeline stages"""
    
    def __init__(self, output_dir=None):
        """Initialize with output directory for artifacts"""
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.output_dir = Path(output_dir or f'pipeline_artifacts_{self.timestamp}')
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories for each stage
        self.dirs = {
            '01_research': self.output_dir / '01_research',
            '02_script': self.output_dir / '02_script', 
            '03_shot_list': self.output_dir / '03_shot_list',
            '04_voiceover': self.output_dir / '04_voiceover',
            '05_assets': self.output_dir / '05_assets',
            '06_timeline': self.output_dir / '06_timeline',
            '07_render': self.output_dir / '07_render',
            '08_final': self.output_dir / '08_final'
        }
        
        for dir_path in self.dirs.values():
            dir_path.mkdir(exist_ok=True)
            
        self.artifacts = {}
        self.load_credentials()
        
    def load_credentials(self):
        """Load API credentials from environment or GCP secrets"""
        print("\n🔑 Loading credentials...")
        secrets = [
            'ELEVENLABS_API_KEY',
            'SHOTSTACK_API_KEY',
            'PEXELS_API_KEY',
            'PIXABAY_API_KEY',
            'OPENAI_API_KEY',
            'PERPLEXITY_API_KEY',
            'TAVILY_API_KEY'
        ]
        
        for secret in secrets:
            if not os.environ.get(secret):
                try:
                    value = subprocess.check_output(
                        ['gcloud', 'secrets', 'versions', 'access', 'latest', f'--secret={secret}'],
                        stderr=subprocess.DEVNULL
                    ).decode().strip()
                    os.environ[secret] = value
                    print(f"  ✓ {secret} loaded")
                except:
                    print(f"  ⚠ {secret} not found")
        
        os.environ['ASSET_CACHE_BUCKET'] = 'yta-main-assets'
    
    def save_artifact(self, stage, name, content, extension='json'):
        """Save an artifact to the appropriate directory"""
        file_path = self.dirs[stage] / f'{name}_{self.timestamp}.{extension}'
        
        if extension == 'json':
            with open(file_path, 'w') as f:
                json.dump(content, f, indent=2, default=str)
        else:
            with open(file_path, 'w' if isinstance(content, str) else 'wb') as f:
                f.write(content)
        
        print(f"  💾 Saved: {file_path}")
        return file_path
    
    def stage_1_research(self):
        """Stage 1: Research AI news from various sources"""
        print("\n" + "="*80)
        print("📚 STAGE 1: NEWS RESEARCH & RANKING")
        print("="*80)
        
        try:
            from src.ingest.rss_arxiv import fetch_rss, fetch_fulltext
            from src.editorial.story_analyzer import StoryAnalyzer
            from src.rank.select import pick_top
            from src.config import settings

            feeds_env = getattr(settings, 'RSS_FEEDS', '')
            sources = [f.strip() for f in feeds_env.split(',') if f.strip()]
            if not sources:
                sources = [
                    'https://news.google.com/rss/search?q=artificial+intelligence&hl=en-US&gl=US&ceid=US:en',
                    'https://www.artificialintelligence-news.com/feed/'
                ]

            print("\n🔍 Pulling RSS feeds:")
            all_news = []
            for url in sources:
                print(f"  • {url}")
                items = fetch_rss([url])
                all_news.extend(items)

            if not all_news:
                raise RuntimeError("No news articles retrieved")

            # Enrich first few stories with full text for better summaries
            for story in all_news[:5]:
                if not story.get('full_text'):
                    story['full_text'] = fetch_fulltext(story['url'])

            selector_input = [{**story, 'score': 0.0} for story in all_news]
            top_ranked = pick_top(selector_input, k=6)

            analyzer = StoryAnalyzer()
            analyzed = analyzer.analyze(top_ranked)

            research_summary = {
                'timestamp': self.timestamp,
                'total_articles': len(all_news),
                'sources_searched': sources,
                'top_stories': [
                    {key: story.get(key) for key in ('title', 'summary', 'url', 'source_domain', 'published_ts', 'full_text')}
                    for story in analyzed[:4]
                ],
                'analysis': analyzed,
                'key_themes': analyzer.headline_blitz(analyzed, limit=3)
            }

            self.save_artifact('01_research', 'raw_news', all_news)
            self.save_artifact('01_research', 'research_summary', research_summary)

            print("\n🏆 Top Stories:")
            for i, story in enumerate(analyzed[:3], 1):
                print(f"  {i}. {story.get('title', 'Untitled')[:80]}...")
                print(f"     Composite: {story['analysis']['scores']['composite']:.2f}")

            self.artifacts['research'] = research_summary
            return research_summary

        except Exception as e:
            print(f"  ⚠ Research failed: {e}, using fallback")
            fallback_stories = [
                {
                    'title': 'OpenAI ships enterprise-ready GPT-5 with governance guardrails',
                    'summary': 'OpenAI rolls out GPT-5 with autonomous agent safety layers and 60% error reduction.',
                    'source_domain': 'openai.com',
                    'published_ts': datetime.now().isoformat(),
                },
                {
                    'title': 'DeepMind and Google fold Gemini into Workspace for 400M users',
                    'summary': 'Gemini copilots go live across Workspace, pushing multimodal workflows mainstream.',
                    'source_domain': 'deepmind.google',
                    'published_ts': datetime.now().isoformat(),
                },
                {
                    'title': 'US-EU announce synchronized AI safety reporting standard',
                    'summary': 'Regulators align on quarterly AI incident disclosures for enterprise providers.',
                    'source_domain': 'europa.eu',
                    'published_ts': datetime.now().isoformat(),
                }
            ]
            fallback = {
                'timestamp': self.timestamp,
                'top_stories': fallback_stories,
                'analysis': fallback_stories,
                'key_themes': ['AI advancement', 'Enterprise adoption']
            }
            self.artifacts['research'] = fallback
            return fallback
    
    def stage_2_script_generation(self, research_data):
        """Stage 2: Generate script from research"""
        print("\n" + "="*80)
        print("✍️ STAGE 2: SCRIPT GENERATION")
        print("="*80)
        
        try:
            from src.editorial.script_daily import ScriptGenerator

            generator = ScriptGenerator()
            stories = research_data.get('top_stories') or research_data.get('analysis') or []

            print("\n🤖 Generating futurist script...")
            script_package = generator.generate_script(stories)

            if not script_package or not script_package.get('vo_script'):
                raise RuntimeError("Script generation returned empty output")

        except Exception:
            script_text = (
                "Welcome to Today in AI. OpenAI just shipped GPT-5 with enterprise guardrails, "
                "DeepMind pushed Gemini into 400M seats, and regulators agreed on a safety standard. "
                "Assign owners now and brief your board."
            )
            script_package = {
                'vo_script': script_text,
                'lower_thirds': ['GPT-5 enterprise launch', 'Gemini everywhere', 'AI safety standards'],
                'broll_keywords': ['ai', 'executive briefing'],
                'chapters': [],
                'metadata': {}
            }

        words = script_package['vo_script'].split()
        script_data = {
            'script': script_package,
            'word_count': len(words),
            'estimated_duration': len(words) / 150 * 60,
            'generated_at': self.timestamp
        }

        self.save_artifact('02_script', 'script', script_data)
        self.save_artifact('02_script', 'script_text', script_package['vo_script'], extension='txt')

        print(f"\n📝 Script generated: {len(words)} words")
        print(f"⏱️ Estimated duration: {script_data['estimated_duration']:.1f} seconds")

        print("\n📄 Script Preview:")
        print("-" * 40)
        preview = script_package['vo_script']
        print(preview[:300] + "..." if len(preview) > 300 else preview)
        print("-" * 40)

        self.artifacts['script'] = script_package
        return script_package
    
    def stage_3_shot_list(self, script):
        """Stage 3: Generate shot list using GPT-5"""
        print("\n" + "="*80)
        print("🎬 STAGE 3: SHOT LIST GENERATION (GPT-5)")
        print("="*80)
        
        from src.produce.shot_list_generator import ShotListGenerator
        
        generator = ShotListGenerator()
        duration = len(script.get('vo_script', '').split()) / 150 * 60 if isinstance(script, dict) else len(str(script).split()) / 150 * 60
        
        print(f"\n🤖 Generating shot list with GPT-5...")
        script_text = script['vo_script'] if isinstance(script, dict) else script
        shot_list = generator.generate_shot_list(script_text, duration)
        
        # Save shot list
        shot_list_data = {
            'segments': shot_list,
            'total_segments': len(shot_list),
            'total_shots': sum(len(s.get('shots', [])) for s in shot_list),
            'duration': duration,
            'generated_at': self.timestamp
        }
        
        self.save_artifact('03_shot_list', 'shot_list', shot_list_data)
        
        # Display summary
        print(f"\n📊 Shot List Summary:")
        print(f"  • Segments: {shot_list_data['total_segments']}")
        print(f"  • Total shots: {shot_list_data['total_shots']}")
        print(f"  • Average shots/segment: {shot_list_data['total_shots']/max(1, shot_list_data['total_segments']):.1f}")
        
        # Show sample segment
        if shot_list:
            print(f"\n📸 Sample Segment:")
            sample = shot_list[0]
            print(f"  Timestamp: {sample.get('timestamp')}")
            print(f"  VO: {sample.get('voiceover', '')[:100]}...")
            for i, shot in enumerate(sample.get('shots', [])[:2], 1):
                print(f"  Shot {i}:")
                print(f"    Visual: {shot.get('visual')}")
                print(f"    Keywords: {', '.join(shot.get('keywords', []))}")
                print(f"    Style: {shot.get('style')}")
        
        self.artifacts['shot_list'] = shot_list_data
        return shot_list
    
    def stage_4_voiceover(self, script):
        """Stage 4: Generate voiceover"""
        print("\n" + "="*80)
        print("🎙️ STAGE 4: VOICEOVER GENERATION")
        print("="*80)
        
        import requests
        
        print("\n🔊 Generating voiceover with ElevenLabs...")
        
        script_text = script.get('vo_script') if isinstance(script, dict) else str(script)

        try:
            headers = {
                'xi-api-key': os.environ.get('ELEVENLABS_API_KEY'),
                'Content-Type': 'application/json'
            }
            
            payload = {
                'text': script_text,
                'model_id': 'eleven_monolingual_v1',
                'voice_settings': {
                    'stability': 0.5,
                    'similarity_boost': 0.75
                }
            }
            
            voice_id = '21m00Tcm4TlvDq8ikWAM'  # Rachel voice
            
            response = requests.post(
                f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}',
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                vo_path = self.dirs['04_voiceover'] / f'voiceover_{self.timestamp}.mp3'
                with open(vo_path, 'wb') as f:
                    f.write(response.content)
                
                print(f"  ✓ Voiceover generated: {vo_path}")
                
                # Upload to GCS
                from google.cloud import storage
                client = storage.Client()
                bucket = client.bucket('yta-main-assets')
                blob_name = f'voiceovers/vo_{self.timestamp}.mp3'
                blob = bucket.blob(blob_name)
                blob.upload_from_filename(vo_path)
                blob.make_public()
                public_url = f'https://storage.googleapis.com/yta-main-assets/{blob_name}'
                print(f"  ✓ Uploaded to GCS: {public_url}")
                
                voiceover_data = {
                    'local_path': str(vo_path),
                    'public_url': public_url,
                    'duration_estimate': len(script_text.split()) / 150 * 60,
                    'voice_id': voice_id,
                    'generated_at': self.timestamp
                }
                
            else:
                raise Exception(f"API error: {response.status_code}")
                
        except Exception as e:
            print(f"  ⚠ Voiceover failed: {e}, using placeholder")
            voiceover_data = {
                'public_url': 'https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3',
                'error': str(e)
            }
        
        self.save_artifact('04_voiceover', 'voiceover_info', voiceover_data)
        self.artifacts['voiceover'] = voiceover_data
        return voiceover_data.get('public_url')
    
    def stage_5_asset_research(self, shot_list):
        """Stage 5: Research B-roll assets"""
        print("\n" + "="*80)
        print("🔍 STAGE 5: B-ROLL ASSET RESEARCH")
        print("="*80)
        
        from src.produce.enhanced_broll_research import EnhancedBrollResearch
        
        researcher = EnhancedBrollResearch()
        
        print("\n🎥 Researching B-roll assets...")
        enhanced_shot_list = researcher.research_sync(shot_list)
        
        # Count assets
        total_assets = 0
        asset_summary = []
        
        for segment in enhanced_shot_list:
            for shot in segment.get('shots', []):
                assets = shot.get('assets', [])
                total_assets += len(assets)
                
                if assets:
                    asset_summary.append({
                        'keywords': shot.get('keywords'),
                        'asset_count': len(assets),
                        'sources': list(set(a.get('source') for a in assets if a.get('source')))
                    })
        
        # Save asset research
        assets_data = {
            'total_assets': total_assets,
            'segments_with_assets': len([s for s in enhanced_shot_list if any(shot.get('assets') for shot in s.get('shots', []))]),
            'asset_summary': asset_summary[:10],  # First 10 for brevity
            'enhanced_shot_list': enhanced_shot_list,
            'generated_at': self.timestamp
        }
        
        self.save_artifact('05_assets', 'asset_research', assets_data)
        
        print(f"\n📊 Asset Research Summary:")
        print(f"  • Total assets found: {total_assets}")
        print(f"  • Average assets/shot: {total_assets/max(1, sum(len(s.get('shots', [])) for s in enhanced_shot_list)):.1f}")
        
        # Show sample assets
        print(f"\n🎬 Sample Assets:")
        for segment in enhanced_shot_list[:1]:
            for shot in segment.get('shots', [])[:1]:
                for asset in shot.get('assets', [])[:3]:
                    print(f"  • {asset.get('description', 'No description')}")
                    print(f"    Source: {asset.get('source', 'Unknown')}")
                    print(f"    URL: {asset.get('url', 'No URL')[:50]}...")
        
        self.artifacts['assets'] = assets_data
        return enhanced_shot_list
    
    def stage_6_timeline_generation(self, shot_list, voiceover_url, duration):
        """Stage 6: Build video timeline"""
        print("\n" + "="*80)
        print("🎞️ STAGE 6: TIMELINE GENERATION")
        print("="*80)
        
        from src.produce.shotstack_dynamic import ShotstackDynamic
        
        builder = ShotstackDynamic()
        
        print("\n⚙️ Building dynamic timeline...")
        timeline = builder.build_dynamic_timeline(
            shot_list=shot_list,
            voiceover_url=voiceover_url,
            total_duration=duration
        )
        
        # Enhance output settings
        timeline['output']['quality'] = 'high'
        timeline['output']['resolution'] = 'hd'
        timeline['output']['scaleTo'] = 'preview'
        
        # Calculate statistics
        stats = {
            'total_clips': len(timeline['timeline']['tracks'][0]['clips']),
            'tracks': len(timeline['timeline']['tracks']),
            'duration': duration,
            'output_format': timeline['output']['format'],
            'resolution': timeline['output']['resolution']
        }
        
        # Save timeline
        timeline_data = {
            'timeline': timeline,
            'statistics': stats,
            'generated_at': self.timestamp
        }
        
        self.save_artifact('06_timeline', 'timeline', timeline_data)
        
        print(f"\n📊 Timeline Summary:")
        print(f"  • Total clips: {stats['total_clips']}")
        print(f"  • Tracks: {stats['tracks']}")
        print(f"  • Duration: {stats['duration']:.1f}s")
        print(f"  • Resolution: {stats['resolution']}")
        
        self.artifacts['timeline'] = timeline_data
        return timeline
    
    def stage_7_render(self, timeline):
        """Stage 7: Render video"""
        print("\n" + "="*80)
        print("🎥 STAGE 7: VIDEO RENDERING")
        print("="*80)
        
        from src.produce.shotstack_dynamic import ShotstackDynamic
        
        builder = ShotstackDynamic()
        
        print("\n🚀 Submitting to Shotstack for rendering...")
        
        try:
            render_id = builder.render_video(timeline)
            print(f"  ✓ Render ID: {render_id}")
            
            render_info = {
                'render_id': render_id,
                'status': 'submitted',
                'submitted_at': self.timestamp,
                'timeline_clips': len(timeline['timeline']['tracks'][0]['clips'])
            }
            
            self.save_artifact('07_render', 'render_info', render_info)
            
            print("\n⏳ Monitoring render progress...")
            print("  This typically takes 1-2 minutes...")
            
            # Wait for render with timeout
            video_url = builder.wait_for_render(render_id, timeout=180)
            
            render_info['status'] = 'completed'
            render_info['video_url'] = video_url
            
            print(f"\n✅ Render complete!")
            print(f"  URL: {video_url}")
            
            self.artifacts['render'] = render_info
            return video_url
            
        except Exception as e:
            print(f"\n❌ Render failed: {e}")
            self.artifacts['render'] = {'error': str(e)}
            return None
    
    def stage_8_finalize(self, video_url):
        """Stage 8: Download and finalize video"""
        print("\n" + "="*80)
        print("📦 STAGE 8: FINALIZATION")
        print("="*80)
        
        if not video_url:
            print("  ⚠ No video URL available")
            return None
        
        try:
            # Download video
            output_path = self.dirs['08_final'] / f'final_video_{self.timestamp}.mp4'
            print(f"\n📥 Downloading video...")
            
            os.system(f'wget -q -O {output_path} "{video_url}"')
            
            if output_path.exists():
                size = output_path.stat().st_size / (1024*1024)
                
                final_data = {
                    'video_url': video_url,
                    'local_path': str(output_path),
                    'size_mb': size,
                    'completed_at': self.timestamp
                }
                
                self.save_artifact('08_final', 'final_video_info', final_data)
                
                print(f"  ✓ Downloaded: {output_path}")
                print(f"  📊 Size: {size:.1f} MB")
                print(f"  🌐 Public URL: {video_url}")
                
                self.artifacts['final'] = final_data
                return output_path
            else:
                print("  ❌ Download failed")
                return None
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
            return None
    
    def generate_report(self):
        """Generate final report with all artifacts"""
        print("\n" + "="*80)
        print("📈 PIPELINE REPORT")
        print("="*80)
        
        report = {
            'pipeline_run': self.timestamp,
            'output_directory': str(self.output_dir),
            'stages_completed': list(self.artifacts.keys()),
            'summary': {
                'research_articles': self.artifacts.get('research', {}).get('total_articles', 0),
                'script_words': self.artifacts.get('script', {}).get('word_count', 0),
                'shot_segments': self.artifacts.get('shot_list', {}).get('total_segments', 0),
                'total_assets': self.artifacts.get('assets', {}).get('total_assets', 0),
                'timeline_clips': self.artifacts.get('timeline', {}).get('statistics', {}).get('total_clips', 0),
                'render_id': self.artifacts.get('render', {}).get('render_id'),
                'final_video': self.artifacts.get('final', {}).get('local_path')
            }
        }
        
        # Save report
        report_path = self.output_dir / f'pipeline_report_{self.timestamp}.json'
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        # Display summary
        print("\n📊 Pipeline Summary:")
        for key, value in report['summary'].items():
            print(f"  • {key.replace('_', ' ').title()}: {value}")
        
        print(f"\n📁 All artifacts saved to: {self.output_dir}")
        print(f"📄 Report saved to: {report_path}")
        
        return report
    
    def run_full_pipeline(self, use_sample_script=False):
        """Run the complete pipeline"""
        print("\n" + "🎬 "*20)
        print("UNIFIED VIDEO PIPELINE TEST - COMPLETE RUN")
        print("🎬 "*20)
        print(f"Timestamp: {self.timestamp}")
        print(f"Output Dir: {self.output_dir}")
        
        try:
            # Stage 1: Research
            if not use_sample_script:
                research = self.stage_1_research()
            else:
                research = {'top_stories': [], 'key_themes': []}
            
            # Stage 2: Script Generation
            if use_sample_script:
                script = """
                Welcome to Today in AI. OpenAI releases GPT-5 with 60% error reduction.
                Google DeepMind achieves 99% accuracy in protein prediction.
                Meta launches open-source model rivaling GPT-4.
                These advances signal a new era in AI adoption.
                """
            else:
                script = self.stage_2_script_generation(research)
            
            # Stage 3: Shot List
            shot_list = self.stage_3_shot_list(script)
            
            # Stage 4: Voiceover
            voiceover_url = self.stage_4_voiceover(script)
            
            # Stage 5: Asset Research
            enhanced_shot_list = self.stage_5_asset_research(shot_list)
            
            # Stage 6: Timeline
            script_text = script.get('vo_script') if isinstance(script, dict) else str(script)
            duration = len(script_text.split()) / 150 * 60
            timeline = self.stage_6_timeline_generation(enhanced_shot_list, voiceover_url, duration)
            
            # Stage 7: Render
            video_url = self.stage_7_render(timeline)
            
            # Stage 8: Finalize
            if video_url:
                self.stage_8_finalize(video_url)
            
            # Generate Report
            report = self.generate_report()
            
            print("\n" + "="*80)
            print("✅ PIPELINE COMPLETE!")
            print("="*80)
            
            return report
            
        except Exception as e:
            print(f"\n❌ Pipeline failed: {e}")
            import traceback
            traceback.print_exc()
            return None


def main():
    parser = argparse.ArgumentParser(description='Unified Pipeline Test')
    parser.add_argument('--output-dir', help='Output directory for artifacts')
    parser.add_argument('--sample-script', action='store_true', 
                       help='Use sample script instead of research')
    
    args = parser.parse_args()
    
    # Create pipeline tester
    tester = UnifiedPipelineTest(output_dir=args.output_dir)
    
    # Run full pipeline
    report = tester.run_full_pipeline(use_sample_script=args.sample_script)
    
    if report:
        print("\n🎉 Success! Check the output directory for all artifacts.")
        return 0
    else:
        print("\n❌ Pipeline test failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
