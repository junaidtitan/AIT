"""Typed Google Sheets source manager used by Stage 1 LangGraph."""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Dict, Iterable, List, Optional, Tuple

from src.ingest.rss_arxiv import fetch_rss_async
from src.models import ScoredStory, StoryInput, StorySource
from src.utils import canonical_url, content_fingerprint, merge_keywords, to_thread
from src.utils.errors import StageFailure

logger = logging.getLogger(__name__)

SERVICE_ACCOUNT_PATH = "/home/junaidqureshi/AIT/sheets_service_account.json"


class ManagerStatus(str, Enum):
    CONNECTED = "connected"
    FALLBACK = "fallback"
    ERROR = "error"


@dataclass
class SheetFetchResult:
    status: ManagerStatus
    details: str


class SimpleSheetsManager:
    """Load sources, company patterns, and scoring knobs from Google Sheets."""

    def __init__(self, sheet_id: Optional[str] = None) -> None:
        self.sheet_id = sheet_id or os.environ.get(
            "NEWS_SHEET_ID", "1J4d4S0mnBeWn5hfHhnc97SPusn9ejz4jWE9oQtK0mgU"
        )
        self.service = None
        self.status = SheetFetchResult(status=ManagerStatus.FALLBACK, details="Service not initialised")
        self._connect()

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------

    def _connect(self) -> None:
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            if os.path.exists(SERVICE_ACCOUNT_PATH):
                credentials = service_account.Credentials.from_service_account_file(
                    SERVICE_ACCOUNT_PATH,
                    scopes=["https://www.googleapis.com/auth/spreadsheets"],
                )
                self.service = build("sheets", "v4", credentials=credentials)
                self.status = SheetFetchResult(ManagerStatus.CONNECTED, "service account")
                logger.info("Connected to Google Sheets via service account")
                return

            # Try default credentials as fallback (runs on GCP)
            from google.auth import default

            credentials, project = default()
            self.service = build("sheets", "v4", credentials=credentials)
            self.status = SheetFetchResult(ManagerStatus.CONNECTED, f"application default ({project})")
            logger.info("Connected to Google Sheets using default credentials: %s", project)
        except Exception as exc:  # pragma: no cover - environment dependent
            logger.warning("Falling back to static sources: %s", exc)
            self.service = None
            self.status = SheetFetchResult(ManagerStatus.FALLBACK, str(exc))

    async def _read_sheet(self, range_name: str) -> List[List[str]]:
        if not self.service:
            raise StageFailure("Sheets API unavailable", payload={"range": range_name})

        def _exec() -> List[List[str]]:
            request = (
                self.service.spreadsheets()
                .values()
                .get(spreadsheetId=self.sheet_id, range=range_name)
            )
            try:
                response = request.execute()
            except Exception as exc:  # pragma: no cover - external dependency
                raise StageFailure(
                    "Sheets API request failed",
                    payload={"range": range_name, "error": str(exc)}
                ) from exc
            return response.get("values", [])

        return await to_thread(_exec)

    # ------------------------------------------------------------------
    # Source/metadata loaders
    # ------------------------------------------------------------------

    def _fallback_sources(self) -> List[StorySource]:
        return [
            StorySource(name="OpenAI Blog", url="https://openai.com/blog/rss.xml", category="company", priority=10),
            StorySource(
                name="Google AI Blog",
                url="https://blog.research.google/feeds/posts/default?alt=rss",
                category="company",
                priority=10,
            ),
            StorySource(name="Anthropic News", url="https://www.anthropic.com/rss.xml", category="company", priority=10),
            StorySource(name="ArXiv AI", url="http://arxiv.org/rss/cs.AI", category="research", priority=8),
            StorySource(
                name="TechCrunch AI", url="https://techcrunch.com/category/artificial-intelligence/feed/", category="news", priority=5
            ),
        ]

    async def aget_sources(self) -> List[StorySource]:
        if not self.service:
            return self._fallback_sources()

        try:
            values = await self._read_sheet("Sources!A2:H200")
        except StageFailure:
            return self._fallback_sources()

        sources: List[StorySource] = []
        for row in values:
            if len(row) < 2:
                continue
            enabled = True
            if len(row) > 6 and row[6]:
                enabled = row[6].lower() in {"yes", "true", "1", "enabled"}
            if not enabled:
                continue
            try:
                sources.append(
                    StorySource(
                        name=row[0] or row[1],
                        url=row[1],
                        category=row[3] if len(row) > 3 and row[3] else "news",
                        priority=int(row[5]) if len(row) > 5 and row[5] else 5,
                        metadata={"sheet_row": row},
                    )
                )
            except Exception as exc:
                logger.debug("Skipping source row %s (%s)", row, exc)
        return sources or self._fallback_sources()

    def get_sources(self) -> List[StorySource]:
        return asyncio.run(self.aget_sources())

    async def aget_companies(self) -> Dict[str, List[str]]:
        if not self.service:
            return self._default_companies()
        try:
            values = await self._read_sheet("Companies!A2:D200")
        except StageFailure:
            return self._default_companies()

        companies: Dict[str, List[str]] = {}
        for row in values:
            if not row or not row[0]:
                continue
            patterns: List[str] = [row[0].lower()]
            if len(row) > 1 and row[1]:
                patterns.extend([p.strip().lower() for p in row[1].split(",") if p.strip()])
            if len(row) > 2 and row[2]:
                patterns.extend([p.strip().lower() for p in row[2].split(",") if p.strip()])
            companies[row[0].lower()] = patterns
        return companies or self._default_companies()

    def get_companies(self) -> Dict[str, List[str]]:
        return asyncio.run(self.aget_companies())

    async def aget_scoring_weights(self) -> Dict[str, float]:
        if not self.service:
            return self._default_weights()
        try:
            values = await self._read_sheet("Scoring!A2:B100")
        except StageFailure:
            return self._default_weights()
        weights: Dict[str, float] = {}
        for key, value in values:
            try:
                weights[key] = float(value)
            except Exception:
                continue
        return weights or self._default_weights()

    def get_scoring_weights(self) -> Dict[str, float]:
        return asyncio.run(self.aget_scoring_weights())

    # ------------------------------------------------------------------
    # Fetch + score pipeline
    # ------------------------------------------------------------------

    async def fetch_ranked_articles(
        self,
        *,
        max_per_source: int = 10,
        hours_filter: Optional[int] = None,
        use_youtube_trends: Optional[bool] = None,
    ) -> List[ScoredStory]:
        sources = await self.aget_sources()
        companies = await self.aget_companies()
        weights = await self.aget_scoring_weights()

        articles = await fetch_rss_async(sources, max_items=max_per_source)
        filtered = self._apply_time_filter(articles, hours_filter)
        scored = [self._score_article(item, companies, weights) for item in filtered]

        if use_youtube_trends is None:
            use_youtube_trends = os.environ.get("USE_YOUTUBE_TRENDS", "true").lower() == "true"
        if use_youtube_trends and scored:
            self._apply_trending_boosts(scored)

        scored.sort(key=lambda story: story.score, reverse=True)
        for idx, story in enumerate(scored, start=1):
            story.rank = idx
        if self.service and scored:
            await self._log_articles(scored[:10])
        return scored

    async def fetch_all_sources(
        self,
        hours_filter: Optional[int] = None,
        use_youtube_trends: Optional[bool] = None,
    ) -> List[Dict]:
        ranked = await self.fetch_ranked_articles(hours_filter=hours_filter, use_youtube_trends=use_youtube_trends)
        return [story.model_dump() for story in ranked]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _apply_time_filter(
        self, stories: Iterable[StoryInput], hours_filter: Optional[int]
    ) -> List[StoryInput]:
        if not hours_filter or hours_filter <= 0:
            return list(stories)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_filter)
        filtered = [story for story in stories if story.published_at and story.published_at.replace(tzinfo=timezone.utc) >= cutoff]
        return filtered

    def _score_article(
        self,
        story: StoryInput,
        companies: Dict[str, List[str]],
        weights: Dict[str, float],
    ) -> ScoredStory:
        text = " ".join(filter(None, [story.title, story.summary or ""])).lower()
        is_research = story.source.category == "research" or "arxiv" in (story.source_domain or "")
        published = story.published_at or datetime.now(timezone.utc)
        age = datetime.now(timezone.utc) - published.replace(tzinfo=timezone.utc)

        score = 0.0
        boosts: Dict[str, float] = {}

        # Freshness
        if is_research:
            if age < timedelta(hours=24):
                inc = weights.get("paper_freshness_24h", 3)
                score += inc
                boosts["freshness:24h"] = inc
            elif age < timedelta(hours=48):
                inc = weights.get("paper_freshness_48h", 2)
                score += inc
                boosts["freshness:48h"] = inc
        else:
            boundaries: List[Tuple[timedelta, str, str]] = [
                (timedelta(hours=1), "news_freshness_1h", "freshness:1h"),
                (timedelta(hours=3), "news_freshness_3h", "freshness:3h"),
                (timedelta(hours=6), "news_freshness_6h", "freshness:6h"),
                (timedelta(hours=12), "news_freshness_12h", "freshness:12h"),
                (timedelta(hours=24), "news_freshness_24h", "freshness:24h"),
                (timedelta(hours=48), "news_freshness_48h", "freshness:48h"),
            ]
            for boundary, weight_key, label in boundaries:
                if age < boundary:
                    inc = weights.get(weight_key, 5)
                    score += inc
                    boosts[label] = inc
                    break

        companies_mentioned: List[str] = []
        for company, patterns in companies.items():
            if any(pattern in text for pattern in patterns):
                inc = weights.get("company_mention", 10)
                score += inc
                boosts[f"company:{company}"] = inc
                companies_mentioned.append(company)

        keyword_hits = {
            "model_release": ["release", "launch", "unveil", "ship", "rolls out"],
            "breakthrough": ["breakthrough", "surpass", "beats", "record", "state-of-the-art"],
            "open_source": ["open source", "open-source", "github"],
            "breaking_news": ["breaking:", "just in:", "exclusive:", "confirmed:"],
            "business_news": ["acqui", "funding", "raises", "series", "valuation", "ipo"],
            "partnership": ["partner", "collaboration", "integration", "teams up"],
        }
        multiplier = 1.0 if is_research else 1.5
        for key, phrases in keyword_hits.items():
            if any(phrase in text for phrase in phrases):
                inc = weights.get(key, 10) * multiplier
                score += inc
                boosts[f"keyword:{key}"] = inc

        score += float(story.source.priority)
        boosts["source_priority"] = float(story.source.priority)

        analysis = {
            "scores": {
                "freshness": boosts.get("freshness:1h", 0)
                + boosts.get("freshness:3h", 0)
                + boosts.get("freshness:6h", 0),
                "company": len(companies_mentioned),
            },
            "keywords": merge_keywords(companies_mentioned),
        }

        return ScoredStory(
            source=story.source,
            title=story.title,
            url=canonical_url(story.url) or story.url,
            summary=story.summary,
            full_text=story.full_text,
            published_at=story.published_at,
            source_domain=story.source_domain,
            extras={
                **story.extras,
                "fingerprint": story.extras.get("fingerprint")
                or content_fingerprint(story.url, story.title),
            },
            analysis=analysis,
            diagnostics={},
            score=score,
            boosts=boosts,
            companies_mentioned=companies_mentioned,
        )

    def _apply_trending_boosts(self, stories: List[ScoredStory]) -> None:
        try:
            from src.ingest.youtube_trending import YouTubeTrendingTracker

            tracker = YouTubeTrendingTracker()
            trending = tracker.get_trending_boost_scores()
            tracker.save_trending_to_sheet()
        except Exception:
            from src.ingest.youtube_trending_simple import get_trending_keywords_simple

            trending = get_trending_keywords_simple()

        for story in stories:
            text = f"{story.title} {story.summary or ''}".lower()
            for keyword, bonus in trending.items():
                if keyword.lower() in text:
                    story.score += bonus
                    story.boosts[f"trend:{keyword}"] = bonus

    async def _log_articles(self, stories: List[ScoredStory]) -> None:
        if not self.service:
            return

        def _append() -> None:
            body = {
                "values": [
                    [
                        datetime.now(timezone.utc).isoformat(),
                        story.title[:100],
                        story.url,
                        story.source.name,
                        f"{story.score:.2f}",
                        ", ".join(story.companies_mentioned),
                        (story.published_at or datetime.now(timezone.utc)).isoformat(),
                    ]
                    for story in stories
                ]
            }
            self.service.spreadsheets().values().append(
                spreadsheetId=self.sheet_id,
                range="Article Log!A2:G",
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body=body,
            ).execute()

        try:
            await to_thread(_append)
        except Exception as exc:  # pragma: no cover - depends on environment
            logger.debug("Failed logging articles: %s", exc)

    # ------------------------------------------------------------------
    # Defaults
    # ------------------------------------------------------------------

    def _default_companies(self) -> Dict[str, List[str]]:
        return {
            "openai": ["openai", "gpt", "chatgpt", "dall-e", "sora"],
            "google": ["google", "deepmind", "gemini", "bard", "palm"],
            "anthropic": ["anthropic", "claude"],
            "meta": ["meta", "facebook", "llama"],
            "microsoft": ["microsoft", "copilot", "azure"],
            "bytedance": ["bytedance", "tiktok", "doubao"],
            "alibaba": ["alibaba", "qwen", "tongyi"],
        }

    def _default_weights(self) -> Dict[str, float]:
        return {
            "paper_freshness_24h": 3,
            "paper_freshness_48h": 2,
            "news_freshness_1h": 40,
            "news_freshness_3h": 35,
            "news_freshness_6h": 30,
            "news_freshness_12h": 20,
            "news_freshness_24h": 15,
            "news_freshness_48h": 8,
            "company_mention": 10,
            "model_release": 15,
            "breakthrough": 12,
            "open_source": 10,
            "breaking_news": 20,
            "business_news": 15,
            "partnership": 12,
        }


__all__ = ["SimpleSheetsManager", "ManagerStatus", "SheetFetchResult"]
