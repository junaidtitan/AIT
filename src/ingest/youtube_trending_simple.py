#!/usr/bin/env python3
"""
Simple YouTube Trending Tracker (No API Key Required)
Tracks commonly trending AI topics based on patterns
"""

import os
from typing import Dict, List
from datetime import datetime

from src.utils import to_thread

def get_trending_keywords_simple() -> Dict[str, float]:
    """
    Get trending AI keywords based on current patterns
    Updates manually based on what's hot
    """

    # Get day of week to vary trends
    day = datetime.now().weekday()

    # Base trending topics (always somewhat relevant)
    base_trends = {
        'gpt': 10,
        'chatgpt': 10,
        'openai': 12,
        'claude': 10,
        'anthropic': 10,
        'gemini': 12,
        'google': 8,
        'llama': 8,
        'meta': 8,
        'mistral': 7,
        'grok': 8,
        'agents': 15,  # Hot topic
        'agi': 12,
        'open source': 15,
        'jailbreak': 10,
        'prompt': 8,
    }

    # Weekly rotating hot topics
    weekly_hot = [
        # Monday - Business news
        {'funding': 20, 'acquisition': 18, 'ipo': 15, 'startup': 12, 'unicorn': 12},
        # Tuesday - Technical
        {'benchmark': 15, 'sota': 18, 'paper': 10, 'research': 10, 'breakthrough': 20},
        # Wednesday - Products
        {'release': 20, 'launch': 20, 'beta': 15, 'preview': 15, 'ship': 18},
        # Thursday - Open Source
        {'open source': 25, 'github': 20, 'hugging face': 18, 'community': 12},
        # Friday - Drama/News
        {'fired': 20, 'lawsuit': 18, 'controversy': 15, 'leaked': 20, 'exclusive': 18},
        # Weekend - Tutorials/Comparisons
        {'tutorial': 12, 'vs': 15, 'comparison': 12, 'review': 12, 'hands on': 15},
        {'guide': 12, 'how to': 12, 'explained': 12, 'deep dive': 15, 'analysis': 12},
    ]

    # Merge base with today's hot topics
    trending = base_trends.copy()
    trending.update(weekly_hot[day])

    # Current events boosts (manually update these)
    current_events = {
        'gpt-5': 25,      # Rumors of GPT-5
        'opus 3.5': 20,   # Claude updates
        'gemini 2': 20,   # Google's next model
        'llama 3.2': 18,  # Meta's updates
        'regulatory': 15, # EU/US AI regulations
        'safety': 12,     # AI safety concerns
        'nvidia': 15,     # NVIDIA earnings/chips
        'apple': 15,      # Apple AI features
        'microsoft': 12,  # Copilot updates
        'amazon': 10,     # AWS AI services
    }

    trending.update(current_events)

    return trending


async def aget_trending_keywords_simple() -> Dict[str, float]:
    """Async helper for use within LangGraph nodes."""
    return await to_thread(get_trending_keywords_simple)


def boost_with_simple_trends(articles: List[Dict]) -> List[Dict]:
    """Apply trending boosts without YouTube API"""

    trending = get_trending_keywords_simple()

    print(f"📺 Applying trending boosts (simple mode)")
    print(f"🔥 Hot keywords today: {', '.join(list(trending.keys())[:8])}")

    boosted_count = 0

    for article in articles:
        text = f"{article.get('title', '')} {article.get('summary', '')}".lower()

        # Calculate trending boost
        boost = 0
        matched = []

        for keyword, score in trending.items():
            if keyword in text:
                boost += score
                matched.append(keyword)

        if boost > 0:
            article['score'] = article.get('score', 0) + boost
            article['trending_keywords'] = matched
            boosted_count += 1

            # Only log significant boosts
            if boost >= 20:
                title = article.get('title', '')[:50]
                keywords = ', '.join(matched[:3])
                print(f"  📈 +{boost:.0f} pts: {title}... ({keywords})")

    # Resort by score
    articles.sort(key=lambda x: x.get('score', 0), reverse=True)

    print(f"  ✅ Boosted {boosted_count} articles based on trends")

    return articles


# Store trending keywords in Google Sheet
def save_trends_to_sheet(trending: Dict[str, float]):
    """Save trending keywords to sheet for visibility"""
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        SHEET_ID = os.environ.get('NEWS_SHEET_ID', '1J4d4S0mnBeWn5hfHhnc97SPusn9ejz4jWE9oQtK0mgU')
        SERVICE_ACCOUNT_FILE = '/home/junaidqureshi/AIT/sheets_service_account.json'

        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            return

        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        service = build('sheets', 'v4', credentials=credentials)

        # Create Trending tab data
        values = [['Keyword', 'Boost', 'Updated']]
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')

        for keyword, score in sorted(trending.items(), key=lambda x: x[1], reverse=True):
            values.append([keyword, f"{score:.0f}", timestamp])

        # Try to update Trending tab
        body = {'values': values}
        service.spreadsheets().values().update(
            spreadsheetId=SHEET_ID,
            range='Trending!A1:C50',
            valueInputOption='RAW',
            body=body
        ).execute()

    except Exception as e:
        # Silently fail if no Trending tab
        pass


if __name__ == "__main__":
    # Test trending keywords
    trends = get_trending_keywords_simple()
    print("\n📊 Today's Trending AI Keywords:")
    print("=" * 50)
    for keyword, boost in sorted(trends.items(), key=lambda x: x[1], reverse=True)[:15]:
        bar = '█' * int(boost / 2)
        print(f"  {keyword:15} {bar} +{boost:.0f}")

    # Save to sheet
    save_trends_to_sheet(trends)
