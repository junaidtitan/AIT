#!/usr/bin/env python3
"""
Shot List Generator using Universal B-Roll Prompt Template
Generates dynamic, professional shot lists with 4-7 second pacing
"""

import re
import json
from typing import List, Dict, Tuple
import subprocess
import os

class ShotListGenerator:
    """Generate detailed shot lists for video production"""
    
    UNIVERSAL_TEMPLATE = """
Role and Goal:
You are an expert video producer and scriptwriter for a fast-paced, high-tech news channel similar to "AI Revolution." Your primary task is to take a raw voiceover (VO) script and transform it into a detailed production-ready shot list. Your output must be perfectly synchronized with the narration, visually engaging, and clear enough for an editor (or an automated video service like Shotstack) to execute.

Core Principles for B-Roll Selection and Pacing:
Pacing and Cadence: Maintain high engagement by switching B-roll clips every 4-7 seconds. A new clip should be introduced at the beginning of a new idea, a key phrase, or a natural pause in the narration. The visuals must never feel static.

Keyword Generation Strategy: For each line of the script, generate a set of B-roll keywords. Do not just use the literal words in the script. Think in three layers:
- Literal Keywords: Direct visual representations of the subject. (e.g., for "quantum chip," use quantum computer, microchip, scientist in lab).
- Conceptual Keywords: Abstract or metaphorical visuals that represent the idea. (e.g., for "unlocking a new state of matter," use glowing energy orb, abstract particle animation, fractal universe, neural network).
- Emotive Keywords: Visuals that convey the feeling or impact of the subject. (e.g., for "fighting corruption," use anonymous hacker, determined politician, worried citizen looking at bills).

Visual Style Guide: Assign a style to each B-roll suggestion to guide the visual tone.
- Cinematic: High-quality footage, often with shallow depth of field, slow motion, or dramatic lighting.
- Abstract/Futuristic: Digital animations, glowing data streams, HUD interfaces, network grids.
- Documentary/Stock: Clean, realistic footage of people, places, or objects.
- Graphic/Text Overlay: Use this when a key term or data point needs to be emphasized on screen over the B-roll.

Output Format:
You must provide the output in a structured Markdown table format. Each row represents a timed segment of the script.

| Timestamp | Voiceover Line | B-Roll Shot List |
|---|---|---|

The "B-Roll Shot List" column must contain the following for each shot:
- Visual: A concise, one-sentence description of the desired shot.
- Keywords: A list of 3-5 keywords based on the strategy above.
- Style: Choose one style from the Visual Style Guide.

Your Task:
Now, using this framework, process the following raw script into a complete shot list table:

"""
    
    def __init__(self):
        """Initialize the shot list generator"""
        # Check if OpenAI API key is set
        self.api_key = os.environ.get('OPENAI_API_KEY')
        if not self.api_key:
            # Try to load from GCP Secret Manager
            try:
                self.api_key = subprocess.check_output(
                    ['gcloud', 'secrets', 'versions', 'access', 'latest', '--secret=OPENAI_API_KEY'],
                    stderr=subprocess.DEVNULL
                ).decode().strip()
                os.environ['OPENAI_API_KEY'] = self.api_key
            except:
                print("Warning: OPENAI_API_KEY not found. Using fallback shot list generation.")
    
    def generate_shot_list(self, script: str, duration: float = None) -> List[Dict]:
        """
        Generate a detailed shot list from a script
        
        Args:
            script: The voiceover script
            duration: Optional total duration in seconds
            
        Returns:
            List of shot segments with timing and keywords
        """
        if self.api_key:
            return self._generate_with_ai(script, duration)
        else:
            return self._generate_fallback(script, duration)
    
    def _generate_with_ai(self, script: str, duration: float) -> List[Dict]:
        """Generate shot list using OpenAI API"""
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.api_key)
            
            # Create the full prompt
            prompt = self.UNIVERSAL_TEMPLATE + script
            
            # Call OpenAI API with GPT-5
            response = client.chat.completions.create(
                model="gpt-5",  # Using GPT-5 for advanced shot list generation
                messages=[
                    {"role": "system", "content": "You are a professional video producer specializing in fast-paced news content. Generate detailed shot lists with specific B-roll descriptions."},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=4000
            )
            
            # Parse the response
            shot_list = self._parse_markdown_table(response.choices[0].message.content)
            if not shot_list:
                raise ValueError("AI returned empty shot list")
            return shot_list
            
        except Exception as e:
            print(f"AI generation failed: {e}, using fallback")
            return self._generate_fallback(script, duration)
    
    def _generate_fallback(self, script: str, duration: float) -> List[Dict]:
        """Generate enhanced shot list without AI - with diverse visuals"""
        # Split script into sentences
        sentences = re.split(r'[.!?]+', script)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not duration:
            # Estimate duration at 150 words per minute
            word_count = len(script.split())
            duration = (word_count / 150) * 60
        
        # Calculate time per segment (aim for 4-7 second cuts)
        segment_duration = min(7, max(4, duration / len(sentences)))
        
        shot_list = []
        current_time = 0
        
        # Define diverse visual themes to avoid repetition
        visual_themes = [
            ('Cinematic', ['establishing shot', 'wide angle', 'dramatic lighting']),
            ('Abstract/Futuristic', ['data visualization', 'particle effects', 'holographic display']),
            ('Documentary/Stock', ['office environment', 'technology workspace', 'modern city']),
            ('Cinematic', ['close-up technology', 'server room', 'quantum computer']),
            ('Abstract/Futuristic', ['neural network', 'AI brain', 'digital transformation']),
            ('Documentary/Stock', ['scientists working', 'research lab', 'innovation hub'])
        ]
        
        for i, sentence in enumerate(sentences):
            # Extract key concepts with more variety
            keywords = self._extract_keywords(sentence)
            
            # Rotate through visual themes for variety
            theme_idx = i % len(visual_themes)
            style, visual_keywords = visual_themes[theme_idx]
            
            # Create varied shots for this segment
            shots = []
            
            # Primary shot with specific visual description
            if 'openai' in sentence.lower() or 'gpt' in sentence.lower():
                visual_desc = "OpenAI headquarters building, modern tech campus"
                shot_keywords = ['OpenAI', 'artificial intelligence', 'tech company'] + keywords[:2]
            elif 'google' in sentence.lower() or 'deepmind' in sentence.lower():
                visual_desc = "Google DeepMind research lab, quantum computing facility"
                shot_keywords = ['Google', 'DeepMind', 'quantum computing'] + keywords[:2]
            elif 'meta' in sentence.lower() or 'llama' in sentence.lower():
                visual_desc = "Meta AI research center, open source development"
                shot_keywords = ['Meta', 'open source', 'AI democratization'] + keywords[:2]
            else:
                visual_desc = f"{visual_keywords[i % len(visual_keywords)]}, {keywords[0] if keywords else 'innovation'}"
                shot_keywords = keywords[:3] + visual_keywords[:2]
            
            shots.append({
                'visual': visual_desc,
                'keywords': list(set(shot_keywords))[:5],  # Unique keywords
                'style': style
            })
            
            # Add secondary shot if segment is long enough with different visuals
            if segment_duration > 5:
                secondary_themes = [
                    "Abstract data flow animation",
                    "Tech professional analyzing holographic display",
                    "Futuristic city skyline with digital overlay",
                    "Close-up of advanced processor chip",
                    "Team collaboration in modern office"
                ]
                shots.append({
                    'visual': secondary_themes[i % len(secondary_themes)],
                    'keywords': keywords[1:4] + ['technology', 'future'],
                    'style': 'Abstract/Futuristic' if i % 2 == 0 else 'Cinematic'
                })
            
            shot_list.append({
                'timestamp': f"{self._seconds_to_timestamp(current_time)}-{self._seconds_to_timestamp(current_time + segment_duration)}",
                'voiceover': sentence[:100] + '...' if len(sentence) > 100 else sentence,
                'shots': shots,
                'duration': segment_duration
            })
            
            current_time += segment_duration
        
        return shot_list
    
    def _parse_markdown_table(self, markdown: str) -> List[Dict]:
        """Parse markdown table output into structured data"""
        segments = []
        
        # Check if response is empty or invalid
        if not markdown or len(markdown.strip()) < 50:
            print(f"Warning: GPT-5 returned short/empty response, using enhanced fallback")
            return []
        
        lines = markdown.split('\n')
        
        for line in lines:
            if '|' in line and 'Timestamp' not in line and '---' not in line:
                parts = line.split('|')
                # Filter out empty parts (from leading/trailing pipes)
                parts = [p for p in parts if p]
                if len(parts) >= 3:
                    timestamp = parts[0].strip()
                    voiceover = parts[1].strip()
                    shots_text = parts[2].strip() if len(parts) > 2 else ""
                    
                    # Parse shots from the cell
                    shots = self._parse_shots(shots_text)
                    
                    # Calculate duration from timestamp
                    duration = self._calculate_duration(timestamp)
                    
                    segments.append({
                        'timestamp': timestamp,
                        'voiceover': voiceover,
                        'shots': shots,
                        'duration': duration
                    })
        
        # If no valid segments parsed, return empty to trigger fallback
        if not segments:
            print(f"Warning: No valid segments parsed from GPT-5 response")
        
        return segments
    
    def _parse_shots(self, shots_text: str) -> List[Dict]:
        """Parse individual shots from markdown cell"""
        shots = []
        shot_blocks = re.split(r'Shot \d+:', shots_text)
        
        for block in shot_blocks[1:]:  # Skip empty first element
            shot = {}
            
            # Extract visual description
            visual_match = re.search(r'^(.+?)<br>', block)
            if visual_match:
                shot['visual'] = visual_match.group(1).strip()
            
            # Extract keywords
            keywords_match = re.search(r'Keywords:\s*(.+?)(?:<br>|$)', block)
            if keywords_match:
                shot['keywords'] = [k.strip() for k in keywords_match.group(1).split(',')]
            
            # Extract style
            style_match = re.search(r'Style:\s*(.+?)(?:<br>|$|\.)', block)
            if style_match:
                shot['style'] = style_match.group(1).strip().rstrip('.')
            
            if shot:
                shots.append(shot)
        
        return shots if shots else [{'visual': 'Generic B-roll', 'keywords': ['technology'], 'style': 'Documentary/Stock'}]
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text"""
        # Common AI/tech terms to look for
        tech_terms = ['AI', 'artificial intelligence', 'machine learning', 'neural', 'algorithm',
                      'data', 'model', 'computing', 'quantum', 'robot', 'automation', 'digital',
                      'software', 'hardware', 'cloud', 'innovation', 'technology', 'breakthrough',
                      'research', 'development', 'startup', 'enterprise', 'platform', 'system']
        
        keywords = []
        text_lower = text.lower()
        
        # Find tech terms in text
        for term in tech_terms:
            if term.lower() in text_lower:
                keywords.append(term)
        
        # Add important words (nouns and verbs)
        words = text.split()
        for word in words:
            if len(word) > 4 and word[0].isupper() and word not in keywords:
                keywords.append(word.lower())
        
        return keywords[:5] if keywords else ['technology', 'innovation', 'future']
    
    def _determine_style(self, text: str) -> str:
        """Determine visual style based on content"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ['breakthrough', 'revolutionary', 'quantum', 'future']):
            return 'Abstract/Futuristic'
        elif any(word in text_lower for word in ['company', 'business', 'market', 'industry']):
            return 'Documentary/Stock'
        elif any(word in text_lower for word in ['announced', 'launched', 'unveiled']):
            return 'Cinematic'
        else:
            return 'Documentary/Stock'
    
    def _calculate_duration(self, timestamp: str) -> float:
        """Calculate duration from timestamp range"""
        try:
            parts = timestamp.split('-')
            if len(parts) == 2:
                start = self._timestamp_to_seconds(parts[0])
                end = self._timestamp_to_seconds(parts[1])
                return end - start
        except:
            pass
        return 6.0  # Default duration
    
    def _timestamp_to_seconds(self, timestamp: str) -> float:
        """Convert MM:SS or M:SS to seconds"""
        try:
            parts = timestamp.strip().split(':')
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 1:
                return float(parts[0])
        except:
            pass
        return 0
    
    def _seconds_to_timestamp(self, seconds: float) -> str:
        """Convert seconds to MM:SS format"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}:{secs:02d}"
    
    def export_for_shotstack(self, shot_list: List[Dict]) -> Dict:
        """Export shot list in Shotstack-compatible format"""
        clips = []
        
        for segment in shot_list:
            start_time = self._timestamp_to_seconds(segment['timestamp'].split('-')[0])
            
            for shot in segment['shots']:
                clip = {
                    'start': start_time,
                    'length': segment['duration'] / len(segment['shots']),
                    'keywords': shot['keywords'],
                    'style': shot['style'],
                    'visual': shot['visual']
                }
                clips.append(clip)
        
        return {
            'clips': clips,
            'total_duration': sum(s['duration'] for s in shot_list)
        }


if __name__ == "__main__":
    # Test the generator
    test_script = """
    Anthropic has just released Claude 3.5 Sonnet's latest update, featuring groundbreaking computer use capabilities.
    This new model can now control desktop applications, browse the web, and execute complex multi-step tasks autonomously.
    Early enterprise adopters are reporting 70% reduction in repetitive workflow automation time.
    """
    
    generator = ShotListGenerator()
    shot_list = generator.generate_shot_list(test_script, duration=30)
    
    print("Generated Shot List:")
    print(json.dumps(shot_list, indent=2))
    
    print("\nShotstack Export:")
    print(json.dumps(generator.export_for_shotstack(shot_list), indent=2))
