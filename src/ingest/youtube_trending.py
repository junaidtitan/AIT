#!/usr/bin/env python3
"""
YouTube Trending AI Videos Tracker
Fetches trending AI topics to boost related news articles
"""

import os
import json
import re
from typing import List, Dict, Set
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import subprocess

class YouTubeTrendingTracker:
    """Track trending AI topics on YouTube"""

    def __init__(self):
        self.api_key = self._get_youtube_api_key()
        self.youtube = None
        if self.api_key:
            self.youtube = build('youtube', 'v3', developerKey=self.api_key)

    def _get_youtube_api_key(self):
        """Get YouTube API key from env or Secret Manager"""
        api_key = os.environ.get('YOUTUBE_API_KEY')
        if not api_key:
            try:
                api_key = subprocess.check_output(
                    ['gcloud', 'secrets', 'versions', 'access', 'latest', '--secret=YOUTUBE_API_KEY'],
                    stderr=subprocess.DEVNULL
                ).decode().strip()
            except:
                pass
        return api_key

    def get_trending_ai_videos(self, max_results=50) -> List[Dict]:
        """Fetch trending AI videos from YouTube"""
        if not self.youtube:
            print("⚠️ YouTube API not configured, using fallback trending terms")
            return self._get_fallback_trending()

        try:
            # Search for AI videos published in last 24 hours, sorted by view count
            yesterday = (datetime.now() - timedelta(days=1)).isoformat() + 'Z'

            request = self.youtube.search().list(
                part="snippet",
                q="artificial intelligence OR AI OR GPT OR ChatGPT OR Gemini OR Claude",
                type="video",
                order="viewCount",
                publishedAfter=yesterday,
                maxResults=max_results,
                relevanceLanguage="en",
                regionCode="US"
            )

            response = request.execute()

            videos = []
            for item in response.get('items', []):
                snippet = item['snippet']
                videos.append({
                    'title': snippet['title'],
                    'channel': snippet['channelTitle'],
                    'description': snippet['description'],
                    'published': snippet['publishedAt'],
                    'video_id': item['id']['videoId']
                })

            return videos

        except HttpError as e:
            print(f"⚠️ YouTube API error: {e}")
            return self._get_fallback_trending()

    def _get_fallback_trending(self) -> List[Dict]:
        """Fallback trending topics when API unavailable"""
        # These are typically trending AI topics
        return [
            {'title': 'GPT-5 Release Date', 'keywords': ['gpt-5', 'openai', 'release']},
            {'title': 'Claude 3.5 Sonnet', 'keywords': ['claude', 'anthropic', 'sonnet']},
            {'title': 'Google Gemini 2.0', 'keywords': ['gemini', 'google', 'bard']},
            {'title': 'AI Agents', 'keywords': ['agents', 'autonomous', 'agentic']},
            {'title': 'Open Source LLMs', 'keywords': ['open source', 'llama', 'mistral']},
        ]

    def extract_trending_keywords(self, videos: List[Dict]) -> Dict[str, float]:
        """Extract and score keywords from trending videos"""
        keyword_counts = {}

        # Common AI terms to track
        ai_terms = {
            'gpt', 'gpt-4', 'gpt-5', 'chatgpt', 'openai',
            'claude', 'anthropic', 'sonnet', 'opus',
            'gemini', 'bard', 'google', 'deepmind',
            'llama', 'meta', 'mistral', 'mixtral',
            'midjourney', 'dall-e', 'stable diffusion',
            'copilot', 'github', 'microsoft',
            'agents', 'agi', 'alignment', 'safety',
            'open source', 'hugging face', 'langchain',
            'tesla', 'grok', 'elon', 'nvidia',
            'apple', 'siri', 'perplexity', 'claude',
            'regulation', 'eu', 'biden', 'china'
        }

        for video in videos:
            text = f"{video.get('title', '')} {video.get('description', '')}".lower()

            # Extract mentioned terms
            for term in ai_terms:
                if term in text:
                    keyword_counts[term] = keyword_counts.get(term, 0) + 1

        # Normalize scores (more mentions = higher boost)
        max_count = max(keyword_counts.values()) if keyword_counts else 1
        trending_keywords = {}
        for keyword, count in keyword_counts.items():
            # Score from 5 to 20 based on frequency
            score = 5 + (15 * count / max_count)
            trending_keywords[keyword] = score

        return trending_keywords

    def get_trending_boost_scores(self) -> Dict[str, float]:
        """Get keyword boost scores based on YouTube trends"""
        videos = self.get_trending_ai_videos()

        if not videos:
            # Default boosts if no data
            return {
                'gpt': 10, 'chatgpt': 10, 'openai': 10,
                'claude': 10, 'anthropic': 10,
                'gemini': 10, 'google': 10,
                'open source': 15, 'agents': 12
            }

        trending_keywords = self.extract_trending_keywords(videos)

        print(f"📺 Found {len(videos)} trending AI videos")
        print(f"🔥 Top trending keywords: {', '.join(list(trending_keywords.keys())[:10])}")

        return trending_keywords

    def save_trending_to_sheet(self, trending_keywords: Dict[str, float]):
        """Save trending keywords to Google Sheet for manual review"""
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            SHEET_ID = os.environ.get('NEWS_SHEET_ID', '1J4d4S0mnBeWn5hfHhnc97SPusn9ejz4jWE9oQtK0mgU')
            SERVICE_ACCOUNT_FILE = '/home/junaidqureshi/AIT/sheets_service_account.json'

            if os.path.exists(SERVICE_ACCOUNT_FILE):
                credentials = service_account.Credentials.from_service_account_file(
                    SERVICE_ACCOUNT_FILE,
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
                service = build('sheets', 'v4', credentials=credentials)

                # Prepare data for Trending tab
                values = [['Keyword', 'Boost Score', 'Last Updated']]
                timestamp = datetime.now().isoformat()

                for keyword, score in sorted(trending_keywords.items(), key=lambda x: x[1], reverse=True):
                    values.append([keyword, f"{score:.1f}", timestamp])

                # Update or create Trending tab
                body = {'values': values}
                service.spreadsheets().values().update(
                    spreadsheetId=SHEET_ID,
                    range='Trending!A1:C50',
                    valueInputOption='RAW',
                    body=body
                ).execute()

                print(f"✅ Saved {len(trending_keywords)} trending keywords to sheet")

        except Exception as e:
            print(f"⚠️ Could not save to sheet: {e}")


# Integration function for pipeline
def boost_articles_with_trends(articles: List[Dict]) -> List[Dict]:
    """Boost article scores based on YouTube trends"""
    tracker = YouTubeTrendingTracker()
    trending_boosts = tracker.get_trending_boost_scores()

    # Save to sheet for visibility
    tracker.save_trending_to_sheet(trending_boosts)

    # Apply boosts to articles
    for article in articles:
        text = f"{article.get('title', '')} {article.get('summary', '')}".lower()

        # Add trending bonus to score
        trending_score = 0
        matched_trends = []

        for keyword, boost in trending_boosts.items():
            if keyword in text:
                trending_score += boost
                matched_trends.append(keyword)

        if trending_score > 0:
            article['score'] = article.get('score', 0) + trending_score
            article['trending_keywords'] = matched_trends
            print(f"  📈 Boosted: {article['title'][:50]}... (+{trending_score:.0f} for {', '.join(matched_trends[:3])})")

    # Re-sort by new scores
    articles.sort(key=lambda x: x.get('score', 0), reverse=True)

    return articles


if __name__ == "__main__":
    # Test the tracker
    tracker = YouTubeTrendingTracker()
    trends = tracker.get_trending_boost_scores()

    print("\n📊 Trending AI Keywords on YouTube:")
    print("=" * 50)
    for keyword, score in sorted(trends.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {keyword:20} +{score:.1f} points")