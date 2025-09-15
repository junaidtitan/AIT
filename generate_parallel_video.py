#!/usr/bin/env python3
"""
Parallel video generation with segment splitting and stitching
Processes multiple segments concurrently for faster generation
"""
import os, sys, subprocess, time, json, threading, queue
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, '/home/junaidqureshi/AIT')

# Load credentials
os.environ['PICTORY_CLIENT_ID'] = subprocess.check_output(['gcloud', 'secrets', 'versions', 'access', 'latest', '--secret=PICTORY_CLIENT_ID']).decode().strip()
os.environ['PICTORY_CLIENT_SECRET'] = subprocess.check_output(['gcloud', 'secrets', 'versions', 'access', 'latest', '--secret=PICTORY_CLIENT_SECRET']).decode().strip()

from src.produce.pictory_api import PictoryAPI
from datetime import datetime
import re

class ParallelVideoGenerator:
    def __init__(self, max_workers=3):
        self.max_workers = max_workers
        self.progress = {}
        self.lock = threading.Lock()
        
    def split_script(self, script, max_words_per_segment=450):
        """Split script into segments of ~3 minutes each (150 wpm)"""
        # Clean script first
        clean_script = re.sub(r'\[CHAPTER \d+:.*?\]', '', script)
        clean_script = re.sub(r'\[ONE TO WATCH.*?\]', '', clean_script)
        clean_script = clean_script.strip()
        
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', clean_script)
        
        segments = []
        current_segment = []
        current_words = 0
        
        for sentence in sentences:
            words = len(sentence.split())
            if current_words + words > max_words_per_segment and current_segment:
                segments.append(' '.join(current_segment))
                current_segment = [sentence]
                current_words = words
            else:
                current_segment.append(sentence)
                current_words += words
        
        if current_segment:
            segments.append(' '.join(current_segment))
        
        return segments
    
    def process_segment(self, segment_num, segment_text, total_segments):
        """Process a single segment"""
        segment_id = f'seg_{segment_num}'
        self.update_progress(segment_id, 'Starting', 0)
        
        try:
            api = PictoryAPI()
            
            # Authenticate
            self.update_progress(segment_id, 'Authenticating', 10)
            api.authenticate()
            
            # Create storyboard
            self.update_progress(segment_id, 'Creating storyboard', 20)
            video_name = f'AI News Segment {segment_num}/{total_segments}'
            storyboard_job_id = api.create_storyboard(segment_text, video_name)
            
            # Wait for storyboard
            self.update_progress(segment_id, 'Processing storyboard', 30)
            for i in range(60):
                status_data = api.check_job_status(storyboard_job_id)
                status = status_data.get('data', {}).get('status', 'unknown')
                
                if status == 'completed':
                    self.update_progress(segment_id, 'Storyboard ready', 50)
                    break
                elif status == 'failed':
                    raise Exception(f'Storyboard failed: {status_data}')
                
                progress = 30 + (20 * i / 60)
                self.update_progress(segment_id, f'Storyboard: {status}', progress)
                time.sleep(10)
            
            # Render video
            self.update_progress(segment_id, 'Starting render', 60)
            render_job_id = api.render_video(storyboard_job_id)
            
            # Wait for render
            for i in range(120):
                status_data = api.check_job_status(render_job_id)
                status = status_data.get('data', {}).get('status', 'unknown')
                
                if status == 'completed':
                    video_url = status_data.get('data', {}).get('videoURL')
                    if not video_url:
                        raise Exception('No video URL in response')
                    
                    # Download segment
                    self.update_progress(segment_id, 'Downloading', 90)
                    output_path = f'/home/junaidqureshi/AIT/starter/data/segment_{segment_num}.mp4'
                    api.download_video(video_url, output_path)
                    
                    self.update_progress(segment_id, 'Complete', 100)
                    return output_path
                    
                elif status == 'failed':
                    raise Exception(f'Render failed: {status_data}')
                
                progress = 60 + (30 * i / 120)
                self.update_progress(segment_id, f'Rendering: {status}', progress)
                time.sleep(10)
            
            raise Exception('Render timed out')
            
        except Exception as e:
            self.update_progress(segment_id, f'Failed: {str(e)}', -1)
            raise
    
    def update_progress(self, segment_id, status, percent):
        """Thread-safe progress update"""
        with self.lock:
            self.progress[segment_id] = {'status': status, 'percent': percent}
    
    def show_progress(self):
        """Display current progress for all segments"""
        with self.lock:
            print('\n' + '='*60)
            print('SEGMENT PROGRESS:')
            for seg_id, info in sorted(self.progress.items()):
                if info['percent'] >= 0:
                    bar = '█' * int(info['percent']/5) + '░' * (20 - int(info['percent']/5))
                    print(f"  {seg_id}: [{bar}] {info['percent']:.0f}% - {info['status']}")
                else:
                    print(f"  {seg_id}: [✗ FAILED] - {info['status']}")
            print('='*60)
    
    def stitch_segments(self, segment_files, output_path):
        """Stitch segments together using ffmpeg"""
        print('\nStitching segments together...')
        
        # Create concat file
        concat_file = '/tmp/concat_list.txt'
        with open(concat_file, 'w') as f:
            for seg_file in segment_files:
                f.write(f"file '{seg_file}'\n")
        
        # Run ffmpeg concat
        cmd = [
            'ffmpeg', '-f', 'concat', '-safe', '0',
            '-i', concat_file, '-c', 'copy', output_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f'FFmpeg failed: {result.stderr}')
        
        # Clean up segments
        for seg_file in segment_files:
            os.remove(seg_file)
        os.remove(concat_file)
        
        return output_path
    
    def generate(self, script_path, output_path):
        """Main generation process"""
        # Load script
        with open(script_path, 'r') as f:
            full_script = f.read()
        
        # Split into segments
        segments = self.split_script(full_script)
        total_segments = len(segments)
        
        print('='*60)
        print('PARALLEL VIDEO GENERATION')
        print('='*60)
        print(f'Total words: {len(full_script.split())}')
        print(f'Segments: {total_segments}')
        print(f'Workers: {self.max_workers}')
        print(f'Est. duration: ~{len(full_script.split())/150:.1f} minutes')
        print('='*60)
        
        # Process segments in parallel
        segment_files = []
        futures = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            for i, segment in enumerate(segments, 1):
                print(f'\nSubmitting segment {i}/{total_segments} ({len(segment.split())} words)')
                future = executor.submit(self.process_segment, i, segment, total_segments)
                futures.append((i, future))
            
            # Monitor progress
            completed = 0
            while completed < len(futures):
                time.sleep(5)
                self.show_progress()
                
                # Check completed futures
                for i, future in futures:
                    if future.done() and f'seg_{i}' in self.progress:
                        if self.progress[f'seg_{i}']['percent'] == 100:
                            completed += 1
                            if future.result() not in segment_files:
                                segment_files.append(future.result())
            
            # Final progress
            self.show_progress()
        
        # Stitch segments
        if len(segment_files) == total_segments:
            final_video = self.stitch_segments(sorted(segment_files), output_path)
            
            # Final stats
            size = os.path.getsize(final_video)
            print('\n' + '='*60)
            print('✅ VIDEO GENERATION COMPLETE!')
            print('='*60)
            print(f'File: {final_video}')
            print(f'Size: {size/1024/1024:.1f} MB')
            print(f'Segments processed: {total_segments}')
            print('='*60)
            
            return final_video
        else:
            raise Exception(f'Only {len(segment_files)}/{total_segments} segments completed')

# Main execution
if __name__ == '__main__':
    generator = ParallelVideoGenerator(max_workers=3)
    
    script_path = '/home/junaidqureshi/AIT/starter/data/drafts/exec_daily_20250912.md'
    output_path = f'/home/junaidqureshi/AIT/starter/data/daily_parallel_{datetime.now().strftime("%Y%m%d_%H%M%S")}.mp4'
    
    try:
        generator.generate(script_path, output_path)
    except Exception as e:
        print(f'\n✗ ERROR: {e}')
        import traceback
        traceback.print_exc()
