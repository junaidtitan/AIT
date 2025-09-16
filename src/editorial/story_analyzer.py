from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

# Keywords tuned for executive-facing AI news
_SHOCK_TERMS = {
    "breakthrough", "surprise", "record", "surge", "collapse", "leak",
    "lawsuit", "ban", "halt", "shutdown", "slam", "explosion", "shock",
    "critical", "urgent", "skyrocket", "crash", "dominates"
}
_FUTURE_TERMS = {
    "roadmap", "pilot", "rollout", "launch", "scale", "platform", "deploy",
    "expansion", "forecast", "strategy", "2025", "2026", "future", "next-gen",
    "pipeline", "commercial", "production", "go-to-market"
}
_TECH_TERMS = {
    "parameter", "tokens", "architecture", "model", "weights", "alignment",
    "quantum", "qubit", "gpu", "tensor", "transformer", "embedding", "diffusion",
    "reinforcement", "fine-tune", "agentic", "vector", "chip", "node", "latency",
    "retrieval", "context window", "multimodal"
}
_AUTHORITY_WEIGHTS = {
    "openai.com": 1.0,
    "deepmind.google": 0.95,
    "anthropic.com": 0.9,
    "meta.com": 0.85,
    "microsoft.com": 0.85,
    "google.com": 0.8,
    "wired.com": 0.75,
    "techcrunch.com": 0.7,
}
_NUMBER_PATTERN = re.compile(r"(?P<value>\d+(?:\.\d+)?)(?P<suffix>%|x|X|\s?billion|\s?million)?", re.IGNORECASE)


@dataclass
class StoryScores:
    shock: float
    future: float
    recency: float
    authority: float
    wow: float
    technical_complexity: float
    composite: float


class AnalogyGenerator:
    """Suggest analogies for complex AI/tech concepts."""

    _LIBRARY: Dict[str, Dict[str, Any]] = {
        "quantum": {
            "keywords": {"quantum", "qubit", "superposition"},
            "analogy": "Picture a logistics network where every route is explored at once—quantum systems work with similar parallel paths."
        },
        "multimodal": {
            "keywords": {"multimodal", "vision", "audio", "video"},
            "analogy": "Think of it as hiring a polyglot analyst who can read slides, listen to calls, and parse spreadsheets simultaneously."
        },
        "agent": {
            "keywords": {"agent", "autonomous", "tool use"},
            "analogy": "It's like promoting a junior analyst to chief of staff—the software now coordinates whole workflows without hand-holding."
        },
        "chip": {
            "keywords": {"chip", "semiconductor", "gpu", "asic"},
            "analogy": "Treat it like a port expansion: more lanes moving compute freight with far less congestion."
        },
        "alignment": {
            "keywords": {"alignment", "safety", "guardrail"},
            "analogy": "Alignment is the AI version of Sarbanes-Oxley—controls that keep powerful systems inside policy rails."
        },
        "synthetic_data": {
            "keywords": {"synthetic", "data engine", "simulation"},
            "analogy": "Imagine a flight simulator for your data science team—synthetic data lets them train without touching production logs."
        },
        "robotics": {
            "keywords": {"robot", "cobot", "manipulation"},
            "analogy": "Think of a warehouse where Kiva bots learned parkour—dexterity jumps mean new categories can go hands-free."
        },
        "trust": {
            "keywords": {"governance", "policy", "auditing", "compliance"},
            "analogy": "Consider it the GDPR moment for AI—the compliance office now sits in every sprint review."
        }
    }

    _DEFAULT = "Net out the jargon: this unlocks a new capability executives can operationalize if they move fast."

    def suggest(self, text: str, keywords: Iterable[str]) -> str:
        lowered = text.lower()
        keyword_set = {k.lower() for k in keywords if k}
        for entry in self._LIBRARY.values():
            if entry["keywords"] & keyword_set or any(term in lowered for term in entry["keywords"]):
                return entry["analogy"]
        return self._DEFAULT


class WowFactorEngine:
    """Detect and amplify wow-factor beats in a story."""

    def compute(self, text: str) -> Dict[str, Any]:
        numbers = [m.group().strip() for m in _NUMBER_PATTERN.finditer(text)]
        wow_terms = [term for term in _SHOCK_TERMS if term in text.lower()]
        wow_score = min(1.0, 0.2 * len(numbers) + 0.3 * len(wow_terms))
        highlight: Optional[str] = None
        if wow_score < 0.4 and numbers:
            highlight = f"That {numbers[0]} stat is the tell executives should brief on."
            wow_score = 0.45
        elif wow_score >= 0.4 and wow_terms:
            highlight = f"It's a {wow_terms[0]} move that will make board decks this quarter."
        return {"wow_score": wow_score, "wow_highlight": highlight}


class StoryAnalyzer:
    """Analyze and rank stories for the futurist scripting engine."""

    def __init__(self) -> None:
        self._analogy = AnalogyGenerator()
        self._wow = WowFactorEngine()

    def analyze(self, stories: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        enriched: List[Dict[str, Any]] = []
        for story in stories:
            text = " ".join(
                str(story.get(field, ""))
                for field in ("title", "summary", "full_text")
            )
            metrics = self._score_story(story)
            wow = self._wow.compute(text)
            keywords = self._extract_keywords(text)
            analogy = self._analogy.suggest(text, keywords)
            enriched_story = {
                **story,
                "analysis": {
                    "scores": metrics.__dict__,
                    "keywords": keywords,
                    "analogy": analogy,
                    "wow_highlight": wow["wow_highlight"],
                    "wow_score": wow["wow_score"],
                    "technical_complexity": metrics.technical_complexity >= 0.5,
                }
            }
            enriched.append(enriched_story)
        enriched.sort(key=lambda s: s["analysis"]["scores"]["composite"], reverse=True)
        return enriched

    def headline_blitz(self, analyzed: List[Dict[str, Any]], limit: int = 4) -> List[str]:
        return [item.get("title", "").strip() for item in analyzed[:limit] if item.get("title")]

    def build_bridge(self, analyzed: List[Dict[str, Any]], limit: int = 3) -> str:
        topics = []
        for item in analyzed[:limit]:
            keywords = item["analysis"].get("keywords", [])
            if keywords:
                topics.append(keywords[0])
        topics = [t for t in topics if t]
        if not topics:
            return "Here's how those moves connect: AI power, adoption speed, and governance pressure are colliding." 
        if len(topics) == 1:
            return f"All eyes stay on {topics[0]}—it's the thread linking every board conversation right now."
        if len(topics) == 2:
            return f"{topics[0].title()} meeting {topics[1]} is the collision shaping Q3 playbooks."
        return f"{topics[0].title()}, {topics[1]}, and {topics[2]} signal the same thing: operators need a plan before the next earnings call."

    def _score_story(self, story: Dict[str, Any]) -> StoryScores:
        text = " ".join(
            str(story.get(field, ""))
            for field in ("title", "summary", "full_text")
        ).lower()
        shock_hits = sum(1 for term in _SHOCK_TERMS if term in text)
        future_hits = sum(1 for term in _FUTURE_TERMS if term in text)
        technical_hits = sum(1 for term in _TECH_TERMS if term in text)

        shock = min(1.0, 0.2 * shock_hits)
        future = min(1.0, 0.2 * future_hits)
        technical = min(1.0, 0.2 * technical_hits)

        recency = self._recency_score(story.get("published_ts"))
        authority = _AUTHORITY_WEIGHTS.get(story.get("source_domain", ""), 0.5)

        wow_base = 0.4 * shock + 0.3 * future + 0.3 * min(1.0, technical + 0.1)
        composite = 0.35 * shock + 0.25 * future + 0.15 * technical + 0.15 * recency + 0.10 * authority
        composite = min(1.0, composite)

        return StoryScores(
            shock=shock,
            future=future,
            recency=recency,
            authority=authority,
            wow=wow_base,
            technical_complexity=technical,
            composite=composite,
        )

    def _recency_score(self, iso_ts: Optional[str]) -> float:
        if not iso_ts:
            return 0.4
        try:
            dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        except ValueError:
            return 0.4
        now = datetime.now(timezone.utc)
        delta = now - dt.replace(tzinfo=timezone.utc)
        days = delta.total_seconds() / 86400
        return max(0.2, min(1.0, 1.0 - (days / 10)))

    def _extract_keywords(self, text: str) -> List[str]:
        lowered = text.lower()
        keywords: List[str] = []
        for term in sorted(_TECH_TERMS | _FUTURE_TERMS | _SHOCK_TERMS, key=len, reverse=True):
            if term in lowered and term not in keywords:
                keywords.append(term)
            if len(keywords) >= 5:
                break
        if not keywords:
            # Fall back to significant nouns from title-like phrases
            words = [w for w in re.findall(r"[a-zA-Z]+", text) if len(w) > 4]
            keywords = sorted(set(words), key=words.count, reverse=True)[:3]
        return keywords


__all__ = ["StoryAnalyzer", "AnalogyGenerator"]
