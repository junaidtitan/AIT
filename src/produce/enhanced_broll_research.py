#!/usr/bin/env python3
"""
Enhanced B-Roll Research with Multi-Layer Keywords
Searches for assets using literal, conceptual, and emotive keywords
"""

import os
import sys
import json
import requests
import asyncio
import aiohttp
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor
import hashlib

class EnhancedBrollResearch:
    """Enhanced B-roll research with multi-layer keyword strategy"""
    
    def __init__(self):
        """Initialize the enhanced B-roll researcher"""
        self.pexels_key = os.environ.get('PEXELS_API_KEY')
        self.pixabay_key = os.environ.get('PIXABAY_API_KEY')
        # Disable GCS for local testing
        self.storage_client = None
        self.cache_bucket = os.environ.get('ASSET_CACHE_BUCKET', 'yta-main-assets')
        
        # Style-specific search modifiers
        self.style_modifiers = {
            'Cinematic': ['cinematic', 'professional', 'dramatic lighting', '4k', 'slow motion'],
            'Abstract/Futuristic': ['abstract', 'digital', 'futuristic', 'animation', 'neon', 'holographic'],
            'Documentary/Stock': ['professional', 'business', 'corporate', 'real', 'authentic'],
            'Graphic/Text Overlay': ['infographic', 'data visualization', 'chart', 'graph', 'text']
        }
    
    async def research_shot_assets(self, shot_list: List[Dict]) -> List[Dict]:
        """
        Research assets for each shot in the shot list
        
        Args:
            shot_list: List of shot segments with keywords and styles
            
        Returns:
            List of segments with populated asset URLs
        """
        tasks = []
        async with aiohttp.ClientSession() as session:
            for segment in shot_list:
                for shot in segment.get('shots', []):
                    task = self._research_single_shot(session, shot)
                    tasks.append(task)
            
            # Research all shots in parallel
            results = await asyncio.gather(*tasks)
        
        # Map results back to shots
        shot_idx = 0
        for segment in shot_list:
            for shot in segment.get('shots', []):
                if shot_idx < len(results):
                    shot['assets'] = results[shot_idx]
                    shot_idx += 1
        
        return shot_list
    
    async def _research_single_shot(self, session: aiohttp.ClientSession, shot: Dict) -> List[Dict]:
        """Research assets for a single shot"""
        keywords = shot.get('keywords', [])
        style = shot.get('style', 'Documentary/Stock')
        
        # Build search queries with different keyword layers
        queries = self._build_layered_queries(keywords, style)
        
        # Search multiple providers in parallel
        assets = []
        for query in queries[:3]:  # Top 3 queries
            # Try Pexels
            if self.pexels_key:
                pexels_assets = await self._search_pexels_async(session, query, style)
                assets.extend(pexels_assets)
            
            # Try Pixabay if needed
            if len(assets) < 3 and self.pixabay_key:
                pixabay_assets = await self._search_pixabay_async(session, query, style)
                assets.extend(pixabay_assets)
        
        # Deduplicate and rank assets
        assets = self._deduplicate_assets(assets)
        assets = self._rank_assets(assets, keywords, style)
        
        # Cache top assets
        if self.storage_client and assets:
            cached_assets = await self._cache_assets(assets[:3])
            return cached_assets
        
        return assets[:3]  # Return top 3 assets
    
    def _build_layered_queries(self, keywords: List[str], style: str) -> List[str]:
        """Build multi-layer search queries"""
        queries = []
        
        # Layer 1: Literal keywords
        if keywords:
            literal_query = ' '.join(keywords[:3])
            queries.append(literal_query)
        
        # Layer 2: Style-enhanced keywords
        style_mods = self.style_modifiers.get(style, [])
        if keywords and style_mods:
            style_query = f"{keywords[0]} {style_mods[0]}"
            queries.append(style_query)
        
        # Layer 3: Conceptual/metaphorical
        conceptual_mappings = {
            'breakthrough': 'light breaking through darkness',
            'innovation': 'futuristic technology',
            'growth': 'plant growing timelapse',
            'disruption': 'explosion shockwave',
            'collaboration': 'hands joining together',
            'intelligence': 'brain neural network',
            'automation': 'robot assembly line',
            'data': 'flowing data streams'
        }
        
        for keyword in keywords:
            if keyword.lower() in conceptual_mappings:
                queries.append(conceptual_mappings[keyword.lower()])
                break
        
        # Layer 4: Emotive/impact keywords
        if 'revolutionary' in ' '.join(keywords).lower():
            queries.append('dramatic transformation change')
        elif 'breakthrough' in ' '.join(keywords).lower():
            queries.append('eureka moment discovery')
        elif 'crisis' in ' '.join(keywords).lower():
            queries.append('urgent warning alert')
        
        return queries if queries else ['technology innovation future']
    
    async def _search_pexels_async(self, session: aiohttp.ClientSession, query: str, style: str) -> List[Dict]:
        """Async search Pexels for assets"""
        if not self.pexels_key:
            return []
        
        headers = {'Authorization': self.pexels_key}
        assets = []
        
        # Prefer videos for dynamic content
        prefer_video = style in ['Cinematic', 'Abstract/Futuristic']
        
        if prefer_video:
            # Search videos first
            url = 'https://api.pexels.com/videos/search'
            params = {'query': query, 'per_page': 5, 'orientation': 'landscape'}
            
            try:
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        for video in data.get('videos', []):
                            # Get highest quality file
                            best_file = None
                            for file in video.get('video_files', []):
                                if file.get('quality') == 'hd' and file.get('width', 0) >= 1920:
                                    best_file = file
                                    break
                            if not best_file and video.get('video_files'):
                                best_file = video['video_files'][0]
                            
                            if best_file:
                                assets.append({
                                    'url': best_file['link'],
                                    'type': 'video',
                                    'duration': video.get('duration', 10),
                                    'width': best_file.get('width', 1920),
                                    'height': best_file.get('height', 1080),
                                    'source': 'pexels',
                                    'query': query,
                                    'id': str(video.get('id'))
                                })
            except Exception as e:
                print(f"Pexels video search error: {e}")
        
        # Fallback to images
        if len(assets) < 3:
            url = 'https://api.pexels.com/v1/search'
            params = {'query': query, 'per_page': 5, 'orientation': 'landscape'}
            
            try:
                async with session.get(url, params=params, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        for photo in data.get('photos', []):
                            assets.append({
                                'url': photo['src']['large2x'],
                                'type': 'image',
                                'width': photo.get('width', 1920),
                                'height': photo.get('height', 1080),
                                'source': 'pexels',
                                'query': query,
                                'id': str(photo.get('id'))
                            })
            except Exception as e:
                print(f"Pexels image search error: {e}")
        
        return assets
    
    async def _search_pixabay_async(self, session: aiohttp.ClientSession, query: str, style: str) -> List[Dict]:
        """Async search Pixabay for assets"""
        if not self.pixabay_key:
            return []
        
        assets = []
        
        # Search videos if style suggests motion
        if style in ['Cinematic', 'Abstract/Futuristic']:
            url = 'https://pixabay.com/api/videos/'
            params = {
                'key': self.pixabay_key,
                'q': query,
                'per_page': 3
            }
            
            try:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        for video in data.get('hits', []):
                            # Get medium or large size
                            video_url = video.get('videos', {}).get('medium', {}).get('url')
                            if not video_url:
                                video_url = video.get('videos', {}).get('large', {}).get('url')
                            
                            if video_url:
                                assets.append({
                                    'url': video_url,
                                    'type': 'video',
                                    'duration': video.get('duration', 10),
                                    'width': video.get('videos', {}).get('medium', {}).get('width', 1920),
                                    'height': video.get('videos', {}).get('medium', {}).get('height', 1080),
                                    'source': 'pixabay',
                                    'query': query,
                                    'id': str(video.get('id'))
                                })
            except Exception as e:
                print(f"Pixabay video search error: {e}")
        
        # Fallback to images
        if len(assets) < 3:
            url = 'https://pixabay.com/api/'
            params = {
                'key': self.pixabay_key,
                'q': query,
                'per_page': 5,
                'image_type': 'photo',
                'orientation': 'horizontal'
            }
            
            try:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        for image in data.get('hits', []):
                            assets.append({
                                'url': image.get('largeImageURL', image.get('webformatURL')),
                                'type': 'image',
                                'width': image.get('imageWidth', 1920),
                                'height': image.get('imageHeight', 1080),
                                'source': 'pixabay',
                                'query': query,
                                'id': str(image.get('id'))
                            })
            except Exception as e:
                print(f"Pixabay image search error: {e}")
        
        return assets
    
    def _deduplicate_assets(self, assets: List[Dict]) -> List[Dict]:
        """Remove duplicate assets based on ID"""
        seen = set()
        unique = []
        
        for asset in assets:
            asset_id = f"{asset.get('source')}_{asset.get('id')}"
            if asset_id not in seen:
                seen.add(asset_id)
                unique.append(asset)
        
        return unique
    
    def _rank_assets(self, assets: List[Dict], keywords: List[str], style: str) -> List[Dict]:
        """Rank assets based on relevance and quality"""
        for asset in assets:
            score = 0
            
            # Type preference based on style
            if style in ['Cinematic', 'Abstract/Futuristic'] and asset['type'] == 'video':
                score += 30
            elif style == 'Documentary/Stock' and asset['type'] == 'image':
                score += 10
            
            # Resolution quality
            if asset.get('width', 0) >= 1920:
                score += 20
            elif asset.get('width', 0) >= 1280:
                score += 10
            
            # Query match (earlier queries are more relevant)
            query_keywords = asset.get('query', '').lower().split()
            for keyword in keywords:
                if keyword.lower() in query_keywords:
                    score += 15
            
            # Source preference
            if asset['source'] == 'pexels':
                score += 5  # Slight preference for Pexels
            
            asset['relevance_score'] = score
        
        # Sort by relevance score
        return sorted(assets, key=lambda x: x.get('relevance_score', 0), reverse=True)
    
    async def _cache_assets(self, assets: List[Dict]) -> List[Dict]:
        """Cache assets to GCS and return cached URLs"""
        if not self.storage_client:
            return assets
        
        cached = []
        bucket = self.storage_client.bucket(self.cache_bucket)
        
        for asset in assets:
            try:
                # Generate cache path
                url_hash = hashlib.md5(asset['url'].encode()).hexdigest()[:8]
                ext = '.mp4' if asset['type'] == 'video' else '.jpg'
                cache_path = f"broll_cache/{asset['source']}/{url_hash}{ext}"
                
                # Check if already cached
                blob = bucket.blob(cache_path)
                if blob.exists():
                    cached_url = f"https://storage.googleapis.com/{self.cache_bucket}/{cache_path}"
                    asset['cached_url'] = cached_url
                    cached.append(asset)
                    continue
                
                # Download and cache
                async with aiohttp.ClientSession() as session:
                    async with session.get(asset['url']) as response:
                        if response.status == 200:
                            content = await response.read()
                            blob.upload_from_string(content)
                            cached_url = f"https://storage.googleapis.com/{self.cache_bucket}/{cache_path}"
                            asset['cached_url'] = cached_url
                            cached.append(asset)
            except Exception as e:
                print(f"Cache error for {asset['url']}: {e}")
                cached.append(asset)  # Use original URL if caching fails
        
        return cached
    
    def research_sync(self, shot_list: List[Dict]) -> List[Dict]:
        """Synchronous wrapper for async research"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.research_shot_assets(shot_list))
        finally:
            loop.close()


if __name__ == "__main__":
    # Test the enhanced B-roll research
    test_shot_list = [
        {
            'timestamp': '0:00-0:06',
            'voiceover': 'Anthropic releases Claude 3.5',
            'shots': [
                {
                    'visual': 'AI company logo reveal',
                    'keywords': ['anthropic', 'claude', 'AI', 'artificial intelligence'],
                    'style': 'Cinematic'
                },
                {
                    'visual': 'Abstract AI visualization',
                    'keywords': ['neural network', 'machine learning', 'digital brain'],
                    'style': 'Abstract/Futuristic'
                }
            ]
        }
    ]
    
    researcher = EnhancedBrollResearch()
    result = researcher.research_sync(test_shot_list)
    
    print("Enhanced B-roll Research Results:")
    print(json.dumps(result, indent=2))