"""YouTube trending intelligence used to inform research-stage scoring."""

from __future__ import annotations

import json
import os
import subprocess
import textwrap
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from src.utils import to_thread


_VIDEO_BATCH = 10  # limit videos sent to LLM for affordability
_DEFAULT_MODEL = os.environ.get("OPENAI_TRENDING_MODEL", "gpt-4o-mini")


class TrendingBoost(BaseModel):
    """Structured boost recommendation returned by the LLM."""

    keyword: str = Field(description="Canonical keyword or phrase to match against stories")
    boost: float = Field(description="Boost score to add when keyword matches", ge=0.0, le=30.0)
    confidence: str = Field(description="Confidence label: high | medium | low")
    companies: List[str] = Field(default_factory=list, description="Associated companies or orgs")
    rationale: str = Field(description="Short reasoning describing the signal")


@dataclass
class TrendingVideo:
    """Raw YouTube video signal used for LLM analysis."""

    video_id: str
    title: str
    description: str
    channel: str
    published: str
    view_count: int
    transcript: Optional[str]

    def to_prompt_block(self) -> str:
        transcript_excerpt = (self.transcript or "").strip()
        if transcript_excerpt:
            transcript_excerpt = textwrap.shorten(transcript_excerpt, width=700, placeholder=" …")
        description_excerpt = textwrap.shorten(self.description or "", width=400, placeholder=" …")
        return textwrap.dedent(
            f"""
            - title: {self.title}
              channel: {self.channel}
              views: {self.view_count}
              published: {self.published}
              description: {description_excerpt}
              transcript_excerpt: {transcript_excerpt or "<missing>"}
            """
        ).strip()


class TrendingLLMAnalyzer:
    """Use an LLM to convert raw videos into actionable boost signals."""

    def __init__(self, model: str = _DEFAULT_MODEL, temperature: float = 0.2) -> None:
        try:
            self.client = ChatOpenAI(model=model, temperature=temperature)
        except Exception as exc:  # pragma: no cover - network/config
            self.client = None
            print(f"⚠️ Unable to initialise ChatOpenAI: {exc}")

    def build_boosts(self, videos: List[TrendingVideo]) -> Dict[str, TrendingBoost]:
        if not self.client or not videos:
            return {}

        blocks = [video.to_prompt_block() for video in videos[:_VIDEO_BATCH]]
        blocks_text = "\n".join(blocks)

        system_prompt = textwrap.dedent(
            """
            You are an AI news signal analyst who monitors high-performing
            YouTube videos to surface urgent themes for our executive research
            pipeline.
            """
        ).strip()

        human_prompt = textwrap.dedent(
            f"""
            Analyse the following list of high-performing AI videos and derive
            boost recommendations for a news ranking system. Focus on the
            companies, product launches, regulatory moves, and technology themes
            executives should prioritise today.

            For EACH distinct signal, output a JSON object with:
            - keyword: concise phrase we can match in article titles/summaries
            - boost: 6-24 scale (higher = stronger urgency/attention)
            - confidence: high | medium | low
            - companies: company or organisation anchors (list)
            - rationale: brief justification (<30 words)

            Guidelines:
            - Merge duplicate signals (e.g. "OpenAI GPT-5" and "GPT-5 leak" → one entry).
            - Do not exceed 12 entries.
            - Prefer precise company/product terms over generic "AI".
            - If a company is the primary actor, include it explicitly in keyword.

            Return strictly valid JSON with top-level key "boosts" that maps to a
            list of objects matching the schema above. No commentary.

            Videos:
            {blocks_text}
            """
        ).strip()

        try:
            response = self.client.invoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=human_prompt),
                ],
                response_format={"type": "json_object"},
            )
        except Exception as exc:  # pragma: no cover - network/config
            print(f"⚠️ LLM trending analysis failed: {exc}")
            return {}

        try:
            data = json.loads(response.content)
        except Exception as exc:
            print(f"⚠️ Could not parse trending analysis JSON: {exc}")
            return {}

        boosts: Dict[str, TrendingBoost] = {}
        items = data.get("boosts", []) if isinstance(data, dict) else []
        for item in items:
            try:
                boost_obj = TrendingBoost.model_validate(item)
            except Exception:
                continue
            keyword = boost_obj.keyword.strip()
            if not keyword:
                continue
            boost_value = max(6.0, min(float(boost_obj.boost), 24.0))
            boost_obj.boost = boost_value
            boosts[keyword.lower()] = boost_obj
        return boosts


class YouTubeTrendingTracker:
    """Track trending AI topics on YouTube and derive smart boosts."""

    def __init__(self) -> None:
        self.api_key = self._get_youtube_api_key()
        self.youtube = None
        self._transcript_client = None
        self._latest_boosts: Dict[str, TrendingBoost] = {}
        if self.api_key:
            self.youtube = build("youtube", "v3", developerKey=self.api_key)
        self._llm = TrendingLLMAnalyzer()

    def _get_youtube_api_key(self) -> Optional[str]:
        api_key = os.environ.get("YOUTUBE_API_KEY")
        if api_key:
            return api_key
        try:
            api_key = (
                subprocess.check_output(
                    [
                        "gcloud",
                        "secrets",
                        "versions",
                        "access",
                        "latest",
                        "--secret=YOUTUBE_API_KEY",
                    ],
                    stderr=subprocess.DEVNULL,
                )
                .decode()
                .strip()
            )
        except Exception:
            api_key = None
        return api_key

    def _load_transcript_client(self) -> None:
        if self._transcript_client is not None:
            return
        try:
            from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore

            self._transcript_client = YouTubeTranscriptApi
        except Exception:
            self._transcript_client = False

    def _fetch_transcript(self, video_id: str) -> Optional[str]:
        self._load_transcript_client()
        if not self._transcript_client:
            return None
        try:
            transcript_items = self._transcript_client.get_transcript(video_id, languages=["en"])
            joined = " ".join(item.get("text", "") for item in transcript_items)
            return joined or None
        except Exception:
            return None

    def _video_details(self, video_ids: List[str]) -> List[TrendingVideo]:
        if not self.youtube:
            return []
        try:
            response = (
                self.youtube.videos()
                .list(part="snippet,statistics", id=",".join(video_ids))
                .execute()
            )
        except HttpError as exc:
            print(f"⚠️ YouTube API error during details fetch: {exc}")
            return []

        videos: List[TrendingVideo] = []
        for item in response.get("items", []):
            snippet = item.get("snippet", {})
            statistics = item.get("statistics", {})
            video_id = item.get("id")
            if not video_id:
                continue
            transcript = self._fetch_transcript(video_id)
            videos.append(
                TrendingVideo(
                    video_id=video_id,
                    title=snippet.get("title", ""),
                    description=snippet.get("description", ""),
                    channel=snippet.get("channelTitle", ""),
                    published=snippet.get("publishedAt", ""),
                    view_count=int(statistics.get("viewCount", 0) or 0),
                    transcript=transcript,
                )
            )
        return videos

    def _search_trending_videos(self, max_results: int = 50) -> List[TrendingVideo]:
        if not self.youtube:
            print("⚠️ YouTube API not configured, using fallback trending signals")
            return []

        yesterday = (datetime.now() - timedelta(days=1)).isoformat() + "Z"
        try:
            request = self.youtube.search().list(
                part="snippet",
                q=(
                    "artificial intelligence OR AI OR GPT OR ChatGPT OR Gemini OR Claude "
                    "OR OpenAI OR Anthropic OR DeepMind OR Nvidia"
                ),
                type="video",
                order="viewCount",
                publishedAfter=yesterday,
                maxResults=max_results,
                relevanceLanguage="en",
                regionCode="US",
            )
            response = request.execute()
        except HttpError as exc:
            print(f"⚠️ YouTube API error during search: {exc}")
            return []

        video_ids = [item.get("id", {}).get("videoId") for item in response.get("items", [])]
        video_ids = [vid for vid in video_ids if vid]
        if not video_ids:
            return []
        return self._video_details(video_ids)

    def _fallback_boosts(self) -> Dict[str, TrendingBoost]:
        fallback = {
            "openai gpt-5": TrendingBoost(
                keyword="OpenAI GPT-5",
                boost=16,
                confidence="medium",
                companies=["OpenAI"],
                rationale="Baseline demand signal for next GPT flagship",
            ),
            "claude 3.5": TrendingBoost(
                keyword="Claude 3.5",
                boost=14,
                confidence="medium",
                companies=["Anthropic"],
                rationale="Anthropic product updates remain steady",
            ),
            "google gemini": TrendingBoost(
                keyword="Google Gemini",
                boost=14,
                confidence="medium",
                companies=["Google"],
                rationale="Gemini roadmap is consistently high-signal",
            ),
            "agentic ai": TrendingBoost(
                keyword="Agentic AI",
                boost=12,
                confidence="low",
                companies=[],
                rationale="Agent frameworks continue to trend",
            ),
        }
        return fallback

    def get_trending_boost_scores(self) -> Dict[str, float]:
        videos = self._search_trending_videos()
        if not videos:
            boosts = self._fallback_boosts()
            self._latest_boosts = boosts
            print(f"🔥 Top trending keywords (fallback): {', '.join(list(boosts.keys())[:10])}")
            return {keyword: boost.boost for keyword, boost in boosts.items()}

        boosts = self._llm.build_boosts(videos)
        if not boosts:
            boosts = self._fallback_boosts()
        self._latest_boosts = boosts

        print(f"📺 Found {len(videos)} trending AI videos")
        print(f"🔥 Top trending keywords: {', '.join(list(boosts.keys())[:10])}")
        return {keyword: boost.boost for keyword, boost in boosts.items()}

    async def aget_trending_boost_scores(self) -> Dict[str, float]:
        return await to_thread(self.get_trending_boost_scores)

    @property
    def latest_boosts(self) -> Dict[str, TrendingBoost]:
        return self._latest_boosts

    def save_trending_to_sheet(self) -> None:
        try:
            from google.oauth2 import service_account

            SHEET_ID = os.environ.get("NEWS_SHEET_ID", "1J4d4S0mnBeWn5hfHhnc97SPusn9ejz4jWE9oQtK0mgU")
            SERVICE_ACCOUNT_FILE = "/home/junaidqureshi/AIT/sheets_service_account.json"

            if not os.path.exists(SERVICE_ACCOUNT_FILE):
                return

            credentials = service_account.Credentials.from_service_account_file(
                SERVICE_ACCOUNT_FILE,
                scopes=["https://www.googleapis.com/auth/spreadsheets"],
            )
            service = build("sheets", "v4", credentials=credentials)

            rows = [["Keyword", "Boost Score", "Confidence", "Companies", "Rationale", "Last Updated"]]
            timestamp = datetime.now().isoformat()
            boosts = self._latest_boosts or self._fallback_boosts()
            for boost in sorted(boosts.values(), key=lambda item: item.boost, reverse=True):
                rows.append(
                    [
                        boost.keyword,
                        f"{boost.boost:.1f}",
                        boost.confidence,
                        ", ".join(boost.companies) if boost.companies else "-",
                        boost.rationale,
                        timestamp,
                    ]
                )

            body = {"values": rows}
            service.spreadsheets().values().update(
                spreadsheetId=SHEET_ID,
                range="'Trending'!A1:F60",
                valueInputOption="RAW",
                body=body,
            ).execute()
            print(f"✅ Saved {len(rows) - 1} trending boosts to sheet")
        except Exception as exc:
            print(f"⚠️ Could not save trending boosts to sheet: {exc}")


def boost_articles_with_trends(articles: List[Dict]) -> List[Dict]:
    tracker = YouTubeTrendingTracker()
    boosts = tracker.get_trending_boost_scores()
    tracker.save_trending_to_sheet()

    for article in articles:
        text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
        for keyword, boost in boosts.items():
            if keyword in text:
                article.setdefault("boosts", {})[f"trend:{keyword}"] = boost
                article["score"] = article.get("score", 0) + boost
    return articles
