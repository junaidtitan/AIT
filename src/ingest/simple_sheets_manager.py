#!/usr/bin/env python3
"""
Simplified Google Sheets Manager for News Sources
Works with existing GCP service account
"""

import os
import hashlib
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import feedparser
import asyncio
import aiohttp

# For environments without Google API libraries, use fallback
try:
    from google.auth import default
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    SHEETS_AVAILABLE = True
except ImportError:
    SHEETS_AVAILABLE = False
    print("Warning: Google Sheets API not available, using fallback sources")

class SimpleSheetsManager:
    """Simple manager for Google Sheets news sources"""

    def __init__(self, sheet_id: str = None):
        self.sheet_id = sheet_id or os.environ.get('NEWS_SHEET_ID', '1J4d4S0mnBeWn5hfHhnc97SPusn9ejz4jWE9oQtK0mgU')
        self.service = None
        self.fallback_sources = self._get_fallback_sources()

        if SHEETS_AVAILABLE:
            # First try service account key file if it exists
            service_account_file = '/home/junaidqureshi/AIT/sheets_service_account.json'
            if os.path.exists(service_account_file):
                try:
                    credentials = service_account.Credentials.from_service_account_file(
                        service_account_file,
                        scopes=['https://www.googleapis.com/auth/spreadsheets']
                    )
                    self.service = build('sheets', 'v4', credentials=credentials)
                    print(f"✓ Connected to Google Sheets using service account key")
                except Exception as e:
                    print(f"⚠️ Could not connect with service account key: {e}")
                    print("   Trying default credentials...")

            # Fall back to default credentials if service account didn't work
            if not self.service:
                try:
                    credentials, project = default()
                    self.service = build('sheets', 'v4', credentials=credentials)
                    print(f"✓ Connected to Google Sheets in project: {project}")
                except Exception as e:
                    print(f"⚠️ Could not connect to sheets: {e}")
                    print("   Using fallback sources")

    def _get_fallback_sources(self) -> List[Dict]:
        """Fallback sources if sheets not available"""
        return [
            {
                'name': 'OpenAI Blog',
                'url': 'https://openai.com/blog/rss.xml',
                'category': 'company',
                'priority': 10
            },
            {
                'name': 'Google AI Blog',
                'url': 'https://blog.research.google/feeds/posts/default?alt=rss',
                'category': 'company',
                'priority': 10
            },
            {
                'name': 'Anthropic News',
                'url': 'https://www.anthropic.com/rss.xml',
                'category': 'company',
                'priority': 10
            },
            {
                'name': 'ArXiv AI',
                'url': 'http://arxiv.org/rss/cs.AI',
                'category': 'research',
                'priority': 8
            },
            {
                'name': 'TechCrunch AI',
                'url': 'https://techcrunch.com/category/artificial-intelligence/feed/',
                'category': 'news',
                'priority': 5
            }
        ]

    def get_sources(self) -> List[Dict]:
        """Get news sources from sheet or fallback"""
        if not self.service:
            return self.fallback_sources

        try:
            # Try to read Sources tab
            range_name = 'Sources!A2:H100'  # Up to 100 sources
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.sheet_id,
                range=range_name
            ).execute()

            values = result.get('values', [])
            sources = []

            for row in values:
                if len(row) >= 2 and row[1]:  # Must have name and URL
                    # Only process enabled sources
                    enabled = True
                    if len(row) > 6:
                        enabled = row[6].lower() in ['yes', 'true', '1', 'enabled']

                    if enabled:
                        sources.append({
                            'name': row[0] if row[0] else 'Unknown',
                            'url': row[1],
                            'category': row[3] if len(row) > 3 else 'news',
                            'priority': int(row[5]) if len(row) > 5 and row[5] else 5
                        })

            print(f"✓ Loaded {len(sources)} sources from Google Sheets")
            return sources if sources else self.fallback_sources

        except Exception as e:
            print(f"⚠️ Could not read sheet: {e}")
            return self.fallback_sources

    def get_companies(self) -> Dict[str, List[str]]:
        """Get company patterns from sheet or defaults"""
        default_companies = {
            'openai': ['openai', 'gpt', 'chatgpt', 'dall-e', 'sora'],
            'google': ['google', 'deepmind', 'gemini', 'bard', 'palm'],
            'anthropic': ['anthropic', 'claude'],
            'meta': ['meta', 'facebook', 'llama'],
            'microsoft': ['microsoft', 'copilot', 'azure'],
            'bytedance': ['bytedance', 'tiktok', 'doubao'],
            'alibaba': ['alibaba', 'qwen', 'tongyi']
        }

        if not self.service:
            return default_companies

        try:
            range_name = 'Companies!A2:D100'
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.sheet_id,
                range=range_name
            ).execute()

            values = result.get('values', [])
            companies = {}

            for row in values:
                if row and row[0]:
                    company_name = row[0].lower().replace(' ', '_')
                    patterns = []

                    # Add company name itself
                    patterns.append(row[0].lower())

                    # Add aliases
                    if len(row) > 1 and row[1]:
                        patterns.extend([a.strip().lower() for a in row[1].split(',')])

                    # Add products
                    if len(row) > 2 and row[2]:
                        patterns.extend([p.strip().lower() for p in row[2].split(',')])

                    companies[company_name] = patterns

            return companies if companies else default_companies

        except:
            return default_companies

    def get_scoring_weights(self) -> Dict[str, float]:
        """Get scoring weights from sheet or defaults"""
        defaults = {
            'freshness_6h': 20,
            'freshness_24h': 10,
            'company_mention': 10,
            'model_release': 15,
            'breakthrough': 12,
            'open_source': 10
        }

        if not self.service:
            return defaults

        try:
            range_name = 'Scoring!A2:B20'
            result = self.service.spreadsheets().values().get(
                spreadsheetId=self.sheet_id,
                range=range_name
            ).execute()

            values = result.get('values', [])
            weights = {}

            for row in values:
                if len(row) >= 2 and row[0] and row[1]:
                    try:
                        weights[row[0]] = float(row[1])
                    except ValueError:
                        pass

            return weights if weights else defaults

        except:
            return defaults

    async def fetch_all_sources(self, hours_filter: int = None, use_youtube_trends: bool = None) -> List[Dict]:
        """Fetch articles from all sources

        Args:
            hours_filter: Only include articles from last N hours (e.g., 24 for last day)
        """
        sources = self.get_sources()
        companies = self.get_companies()
        weights = self.get_scoring_weights()

        # Get filter from environment if not specified
        if hours_filter is None:
            hours_filter = int(os.environ.get('NEWS_HOURS_FILTER', '0'))

        all_articles = []

        async with aiohttp.ClientSession() as session:
            tasks = []
            for source in sources:
                tasks.append(self._fetch_source(session, source))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, list):
                    all_articles.extend(result)

        # Apply time filter if specified
        if hours_filter > 0:
            cutoff_time = datetime.now() - timedelta(hours=hours_filter)
            before_filter = len(all_articles)

            filtered_articles = []
            for article in all_articles:
                # Handle different date formats
                pub_date = article.get('published_date')
                if isinstance(pub_date, str):
                    try:
                        pub_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                    except:
                        pub_date = datetime.now()  # Default to now if parsing fails

                if pub_date and pub_date > cutoff_time:
                    filtered_articles.append(article)

            all_articles = filtered_articles
            print(f"  ⏰ Time filter: {before_filter} → {len(all_articles)} articles (last {hours_filter}h)")

        # Score articles
        for article in all_articles:
            article['score'] = self._score_article(article, companies, weights)

        # Sort by score
        all_articles.sort(key=lambda x: x['score'], reverse=True)

        # Apply YouTube trending boosts if enabled (default: true)
        if use_youtube_trends is None:
            use_youtube_trends = os.environ.get('USE_YOUTUBE_TRENDS', 'true').lower() == 'true'

        if use_youtube_trends and all_articles:
            try:
                # Try simple trending first (no API needed)
                from src.ingest.youtube_trending_simple import boost_with_simple_trends
                print("\n📺 Applying trending boosts...")
                all_articles = boost_with_simple_trends(all_articles)
            except ImportError:
                # Fall back to API version if available
                try:
                    from src.ingest.youtube_trending import boost_articles_with_trends
                    all_articles = boost_articles_with_trends(all_articles)
                except Exception as e:
                    print(f"  ⚠️ Could not apply trending boosts: {e}")

        # Log top articles back to sheet if possible
        if self.service and all_articles:
            self._log_articles(all_articles[:10])

        return all_articles

    async def _fetch_source(self, session: aiohttp.ClientSession, source: Dict) -> List[Dict]:
        """Fetch articles from a single source"""
        try:
            async with session.get(source['url'], timeout=10) as response:
                content = await response.text()
                feed = feedparser.parse(content)

                articles = []
                for entry in feed.entries[:10]:  # Max 10 per source
                    published = datetime.now()
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        published = datetime(*entry.published_parsed[:6])

                    articles.append({
                        'title': entry.get('title', ''),
                        'url': entry.get('link', ''),
                        'summary': entry.get('summary', ''),
                        'source_name': source['name'],
                        'source_category': source['category'],
                        'published_date': published,
                        'source_priority': source['priority']
                    })

                return articles

        except Exception as e:
            print(f"  Failed to fetch {source['name']}: {e}")
            return []

    def _score_article(self, article: Dict, companies: Dict, weights: Dict) -> float:
        """Score an article based on various factors"""
        score = 0.0
        text = f"{article['title']} {article['summary']}".lower()

        # Determine source type
        source_name = article.get('source_name', '').lower()
        source_category = article.get('source_category', '').lower()

        # Check if it's a research/paper source
        is_research = (
            'arxiv' in source_name or
            'papers' in source_name or
            source_category == 'research' or
            'arxiv:' in text[:100] or  # Only check beginning
            'abstract:' in text[:100] or
            'announce type:' in text[:100]  # ArXiv marker
        )

        # Enhanced freshness scoring (different for papers vs news)
        pub_date = article.get('published_date', datetime.now())
        if isinstance(pub_date, str):
            try:
                pub_date = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
            except:
                pub_date = datetime.now()

        age = datetime.now() - pub_date

        # Differential freshness scoring
        if is_research:
            # ArXiv papers: Much lower freshness bonus (they're always "fresh")
            if age < timedelta(hours=24):
                score += weights.get('paper_freshness_24h', 3)  # Small bonus for today's papers
            elif age < timedelta(hours=48):
                score += weights.get('paper_freshness_48h', 2)  # Tiny bonus for recent papers
            # Papers older than 48h get no freshness bonus
        else:
            # Real news/releases: Higher freshness bonus
            if age < timedelta(hours=1):
                score += weights.get('news_freshness_1h', 40)  # BREAKING news
            elif age < timedelta(hours=3):
                score += weights.get('news_freshness_3h', 35)  # Very fresh news
            elif age < timedelta(hours=6):
                score += weights.get('news_freshness_6h', 30)  # Fresh news
            elif age < timedelta(hours=12):
                score += weights.get('news_freshness_12h', 20)  # Today's news
            elif age < timedelta(hours=24):
                score += weights.get('news_freshness_24h', 15)  # Recent news
            elif age < timedelta(hours=48):
                score += weights.get('news_freshness_48h', 8)   # Yesterday's news
            # Older than 48h gets no freshness bonus

        # Company mentions
        for company, patterns in companies.items():
            for pattern in patterns:
                if pattern in text:
                    score += weights.get('company_mention', 10)
                    article['companies_mentioned'] = article.get('companies_mentioned', [])
                    article['companies_mentioned'].append(company)
                    break

        # Keywords (boost more for non-research sources)
        boost_multiplier = 1.0 if is_research else 1.5  # 50% boost for real news

        if any(word in text for word in ['release', 'launch', 'announce', 'unveil', 'ship', 'rolls out']):
            score += weights.get('model_release', 15) * boost_multiplier
        if any(word in text for word in ['breakthrough', 'surpass', 'beats', 'record', 'state-of-the-art']):
            score += weights.get('breakthrough', 12) * boost_multiplier
        if 'open source' in text or 'open-source' in text or 'github' in text:
            score += weights.get('open_source', 10) * boost_multiplier

        # Additional news-specific bonuses
        if not is_research:
            if any(word in text for word in ['breaking:', 'just in:', 'exclusive:', 'confirmed:']):
                score += weights.get('breaking_news', 20)
            if any(word in text for word in ['acqui', 'funding', 'raises', 'series', 'valuation', 'ipo']):
                score += weights.get('business_news', 15)
            if any(word in text for word in ['partner', 'collaboration', 'integration', 'teams up']):
                score += weights.get('partnership', 12)

        # Source priority
        score += article['source_priority']

        return score

    def _log_articles(self, articles: List[Dict]):
        """Log articles back to sheet"""
        try:
            values = []
            for article in articles:
                values.append([
                    datetime.now().isoformat(),
                    article['title'][:100],
                    article['url'],
                    article['source_name'],
                    str(article['score']),
                    ', '.join(article.get('companies_mentioned', [])),
                    article['published_date'].isoformat() if hasattr(article['published_date'], 'isoformat') else str(article['published_date'])
                ])

            body = {'values': values}
            self.service.spreadsheets().values().append(
                spreadsheetId=self.sheet_id,
                range='Article Log!A2:G',
                valueInputOption='RAW',
                insertDataOption='INSERT_ROWS',
                body=body
            ).execute()

        except:
            pass  # Don't fail on logging

# Test function
async def test():
    """Test the sheet manager"""
    print("\n🧪 Testing Simple Sheets Manager...")
    print("=" * 50)

    manager = SimpleSheetsManager()

    # Get sources
    sources = manager.get_sources()
    print(f"\n📰 Found {len(sources)} sources:")
    for source in sources[:3]:
        print(f"  - {source['name']}: Priority {source['priority']}")

    # Get companies
    companies = manager.get_companies()
    print(f"\n🏢 Tracking {len(companies)} companies")

    # Fetch articles
    print("\n🔍 Fetching articles...")
    articles = await manager.fetch_all_sources()

    print(f"\n📊 Top articles (by score):")
    for i, article in enumerate(articles[:5], 1):
        print(f"\n{i}. Score: {article['score']:.1f}")
        print(f"   Title: {article['title'][:80]}...")
        print(f"   Source: {article['source_name']}")
        if 'companies_mentioned' in article:
            print(f"   Companies: {', '.join(article['companies_mentioned'])}")

    return articles

if __name__ == "__main__":
    # Run test
    articles = asyncio.run(test())