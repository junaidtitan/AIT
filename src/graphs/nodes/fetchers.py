"""Fetch nodes for the research LangGraph."""

from __future__ import annotations

from typing import Dict

from src.graphs.state import ResearchState
from src.ingest.rss_arxiv import fetch_rss_async
from src.ingest.simple_sheets_manager import SimpleSheetsManager
from src.ingest.youtube_trending import YouTubeTrendingTracker
from src.ingest.youtube_trending_simple import get_trending_keywords_simple


async def load_sheet_metadata(state: ResearchState) -> ResearchState:
    manager = SimpleSheetsManager()
    sources = await manager.aget_sources()
    companies = await manager.aget_companies()
    weights = await manager.aget_scoring_weights()

    state.sources = sources
    state.companies = companies
    state.scoring_weights = weights
    state.metadata.setdefault("rank_weights", weights)
    state.metadata["sheet_status"] = {
        "status": manager.status.status.value,
        "details": manager.status.details,
    }
    state.diagnostics.record(
        "info",
        "loaded_sources",
        count=len(sources),
        status=manager.status.status.value,
    )

    trending: Dict[str, float] = {}
    try:
        tracker = YouTubeTrendingTracker()
        trending = await tracker.aget_trending_boost_scores()
    except Exception:
        trending = get_trending_keywords_simple()
    state.trending_keywords = trending
    state.diagnostics.record(
        "info",
        "trending_keywords",
        count=len(trending),
    )
    return state


async def fetch_story_feeds(state: ResearchState) -> ResearchState:
    if not state.sources:
        return state
    articles = await fetch_rss_async(state.sources, max_items=10)
    state.raw_stories = articles
    state.diagnostics.record(
        "info",
        "fetched_articles",
        count=len(state.raw_stories),
    )
    return state
