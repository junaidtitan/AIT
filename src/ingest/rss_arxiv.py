"""Async RSS ingestion utilities for LangGraph Stage 1."""

from __future__ import annotations

import asyncio
import datetime as dt
from typing import Iterable, List
from urllib.parse import urlparse

import feedparser
import httpx
from bs4 import BeautifulSoup
from readability import Document

from src.models import StoryInput, StorySource
from src.utils import canonical_url, content_fingerprint, normalize_text, run_with_retry, with_timeout
from src.utils.errors import FetchTimeout

_DEFAULT_TIMEOUT = 10.0


def _domain_of(url: str | None) -> str | None:
    if not url:
        return None
    try:
        parsed = urlparse(url)
        return parsed.netloc or None
    except ValueError:
        return None


async def _fetch_feed(client: httpx.AsyncClient, source: StorySource, *, max_items: int, timeout: float) -> List[StoryInput]:
    async def _do_request() -> httpx.Response:
        return await client.get(source.url, timeout=timeout)

    try:
        response = await run_with_retry(_do_request, attempts=3, wait_initial=0.5, wait_max=5.0)
    except Exception as exc:  # pragma: no cover - network issues exercised in integration tests
        raise FetchTimeout(f"Failed to fetch RSS feed from {source.url}") from exc

    parsed = feedparser.parse(response.content)
    stories: List[StoryInput] = []
    for entry in parsed.entries[:max_items]:
        link = getattr(entry, "link", None)
        title = normalize_text(getattr(entry, "title", ""))
        if not link or not title:
            continue

        published_struct = getattr(entry, "published_parsed", None)
        published_at = None
        if published_struct:
            published_at = dt.datetime(*published_struct[:6], tzinfo=dt.timezone.utc)
        item = StoryInput(
            source=source,
            title=title,
            url=canonical_url(link) or link,
            summary=normalize_text(getattr(entry, "summary", "")),
            published_at=published_at,
            full_text=None,
            source_domain=_domain_of(link),
            extras={"fingerprint": content_fingerprint(link, title)},
        )
        stories.append(item)
    return stories


async def fetch_rss_async(
    sources: Iterable[StorySource],
    *,
    max_items: int = 20,
    timeout: float = _DEFAULT_TIMEOUT,
    concurrency: int = 5,
) -> List[StoryInput]:
    """Fetch RSS content asynchronously for all sources."""
    sources_list = list(sources)
    if not sources_list:
        return []

    async with httpx.AsyncClient(follow_redirects=True) as client:
        semaphore = asyncio.Semaphore(concurrency)
        results: List[StoryInput] = []
        tasks = []

        async def _runner(src: StorySource) -> None:
            async with semaphore:
                items = await _fetch_feed(client, src, max_items=max_items, timeout=timeout)
                results.extend(items)

        for source in sources_list:
            tasks.append(asyncio.create_task(_runner(source)))

        await asyncio.gather(*tasks)
        return results


async def fetch_fulltext_async(url: str, *, timeout: float = _DEFAULT_TIMEOUT) -> str | None:
    """Retrieve cleaned article text asynchronously."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=timeout) as client:
        try:
            response = await with_timeout(client.get(url), timeout)
        except Exception as exc:  # pragma: no cover - network issues exercised in integration tests
            raise FetchTimeout(f"Full-text request timed out for {url}") from exc
        document = Document(response.text)
        soup = BeautifulSoup(document.summary(), "html5lib")
        text = soup.get_text(" ", strip=True)
        return text or None


def fetch_rss(urls: List[str]) -> List[dict]:
    """Legacy synchronous wrapper returning dictionaries for backwards compatibility."""
    sources = [StorySource(name=url, url=url) for url in urls]
    results = asyncio.run(fetch_rss_async(sources))
    return [story.model_dump() for story in results]


def fetch_fulltext(url: str) -> str | None:
    """Legacy synchronous wrapper for full text extraction."""
    return asyncio.run(fetch_fulltext_async(url))


__all__ = [
    "fetch_rss_async",
    "fetch_fulltext_async",
    "fetch_rss",
    "fetch_fulltext",
]
