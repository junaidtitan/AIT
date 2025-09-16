from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

from ..config import settings
from .story_analyzer import StoryAnalyzer
from .structure_validator import StructureValidator
from .tone_enhancer import ToneEnhancer
from .transition_generator import TransitionGenerator
from .cta_generator import CTAGenerator

TEMPLATE_DIR = Path(__file__).resolve().parents[2] / "templates"
MAIN_TEMPLATE = (TEMPLATE_DIR / "futurist_briefing_main.txt").read_text(encoding="utf-8")
SEGMENT_DIR = TEMPLATE_DIR / "segment_templates"
SEGMENT_TEMPLATES = {
    "news": (SEGMENT_DIR / "news.txt").read_text(encoding="utf-8"),
    "funding": (SEGMENT_DIR / "funding.txt").read_text(encoding="utf-8"),
    "research": (SEGMENT_DIR / "research.txt").read_text(encoding="utf-8"),
    "policy": (SEGMENT_DIR / "policy.txt").read_text(encoding="utf-8"),
}


def _render_template(template: str, values: Dict[str, str]) -> str:
    result = template
    for key, value in values.items():
        result = result.replace(f"{{{{{key}}}}}", value)
    return result


def _first_sentence(text: str, fallback: str) -> str:
    if not text:
        return fallback
    parts = [p.strip() for p in str(text).replace("\n", " ").split(".") if p.strip()]
    return parts[0] + "." if parts else fallback


def _determine_segment_type(story: Dict[str, Any]) -> str:
    text = " ".join(str(story.get(field, "")) for field in ("category", "title", "summary", "full_text")).lower()
    if any(term in text for term in ("funding", "raise", "investment", "series")):
        return "funding"
    if any(term in text for term in ("research", "paper", "study", "arxiv", "breakthrough")):
        return "research"
    if any(term in text for term in ("policy", "regulation", "bill", "law", "government")):
        return "policy"
    return "news"


class ScriptGenerator:
    """Generate futurist daily scripts from analyzed stories."""

    def __init__(self) -> None:
        self.analyzer = StoryAnalyzer()
        self.validator = StructureValidator()
        self.transitions = TransitionGenerator()
        self.cta = CTAGenerator()
        self.tone = ToneEnhancer(enable_llm=os.getenv("TONE_ENHANCER_LLM", "false").lower() == "true")

    def generate_script(self, stories: List[Dict[str, Any]]) -> Dict[str, Any]:
        analyzed = self.analyzer.analyze(stories or [])
        if not analyzed:
            return self._fallback_response()

        package = None
        result = None
        for _ in range(2):
            package = self._compose_package(analyzed)
            result = self.validator.validate(package)
            if result.passed:
                break
        if not result or not result.passed:
            package = self._fallback_package(analyzed)
            result = self.validator.validate(package)

        script_text = _render_template(MAIN_TEMPLATE, {
            "opening_hook": package["acts"]["act1"]["hook"],
            "headline_blitz": "\n".join(f"• {h}" for h in package["headline_blitz"]),
            "bridge_sentence": package["bridge_sentence"],
            "segment_blocks": "\n\n".join(segment["rendered"] for segment in package["segments"]),
            "closing_reflection": package["acts"]["act3"]["closing"],
            "cta_prompt": package["cta"]["question"],
            "sign_off": package["acts"]["act3"].get("sign_off", "Stay sharp — JunaidQ AI News"),
        })

        tone_result = self.tone.enhance(script_text)
        package["acts"]["act2"]["body"] = tone_result["text"]

        output = {
            "vo_script": tone_result["text"],
            "lower_thirds": [segment["headline"] for segment in package["segments"]],
            "broll_keywords": self._aggregate_keywords(package["segments"]),
            "chapters": [],
            "metadata": {
                "validator": {
                    "passed": result.passed,
                    "score": result.score,
                    "missing": result.missing,
                },
                "structure": {
                    "acts": package["acts"],
                    "segments": [{k: v for k, v in segment.items() if k != "rendered"} for segment in package["segments"]],
                    "headline_blitz": package["headline_blitz"],
                    "bridge_sentence": package["bridge_sentence"],
                    "cta": package["cta"],
                    "tone": {"llm_used": tone_result["llm_used"]},
                },
            },
        }
        return output

    def _compose_package(self, analyzed: List[Dict[str, Any]]) -> Dict[str, Any]:
        top_stories = analyzed[:3]
        headline_blitz = self.analyzer.headline_blitz(analyzed, limit=4)
        bridge_sentence = self.analyzer.build_bridge(analyzed)

        segments = []
        for idx, story in enumerate(top_stories):
            analysis = story["analysis"]
            segment_type = _determine_segment_type(story)
            template = SEGMENT_TEMPLATES.get(segment_type, SEGMENT_TEMPLATES["news"])
            keywords = analysis.get("keywords", [])
            primary_keyword = keywords[0] if keywords else "AI"
            what_text = _first_sentence(story.get("summary") or story.get("full_text", ""), story.get("title", ""))
            so_what_text = self._compose_so_what(primary_keyword, analysis)
            now_what_text = self._compose_now_what(primary_keyword, analysis)
            wow_factor = analysis.get("wow_highlight") or f"Wow metric: {int(analysis.get('wow_score', 0) * 100)}% heat on this move."
            transition_tag_candidates = [segment_type, "momentum", "closing" if idx == len(top_stories) - 1 else "signal_shift"]
            transition_phrase = self.transitions.pick(transition_tag_candidates)
            rendered = _render_template(template, {
                "headline": story.get("title", ""),
                "what": what_text,
                "so_what": so_what_text,
                "now_what": now_what_text,
                "analogy": analysis.get("analogy", ""),
                "wow_factor": wow_factor,
                "transition": transition_phrase,
            })
            segments.append({
                "headline": story.get("title", ""),
                "what": what_text,
                "so_what": so_what_text,
                "now_what": now_what_text,
                "analogy": analysis.get("analogy", ""),
                "wow_factor": wow_factor,
                "transition": transition_phrase,
                "keywords": keywords,
                "segment_type": segment_type,
                "rendered": rendered,
            })

        topic_for_cta = segments[0]["keywords"][0] if segments and segments[0]["keywords"] else "AI adoption"
        cta_payload = self.cta.generate(topic_for_cta)

        acts = {
            "act1": {
                "hook": self._compose_opening(headline_blitz),
                "bridge": bridge_sentence,
            },
            "act2": {
                "segments": segments,
                "body": "",
            },
            "act3": {
                "closing": self._compose_closing(analyzed),
                "cta": cta_payload,
                "sign_off": "Stay sharp — JunaidQ AI News",
            },
        }

        return {
            "acts": acts,
            "segments": segments,
            "headline_blitz": headline_blitz,
            "bridge_sentence": bridge_sentence,
            "cta": cta_payload,
        }

    def _fallback_package(self, analyzed: List[Dict[str, Any]]) -> Dict[str, Any]:
        top = analyzed[0]
        basic_segment = {
            "headline": top.get("title", "AI is moving fast"),
            "what": _first_sentence(top.get("summary", ""), top.get("title", "")),
            "so_what": "Executive takeaway: budget, policy, and ops teams must sync on this now.",
            "now_what": "Action: assign an owner to pressure-test the opportunity within 7 days.",
            "analogy": top["analysis"].get("analogy", "This is a decisive shift."),
            "wow_factor": top["analysis"].get("wow_highlight") or "This is the board-level jolt this week.",
            "transition": "Which begs the question...",
            "keywords": top["analysis"].get("keywords", []),
            "segment_type": "news",
            "rendered": "",
        }
        template = SEGMENT_TEMPLATES["news"]
        basic_segment["rendered"] = _render_template(template, basic_segment)
        headline_blitz = [basic_segment["headline"]]
        bridge = "Every signal points to AI budgets accelerating despite governance anxiety."
        cta_payload = self.cta.generate(basic_segment["keywords"][0] if basic_segment["keywords"] else "AI strategy")
        acts = {
            "act1": {"hook": f"Today in AI: {basic_segment['headline']}", "bridge": bridge},
            "act2": {"segments": [basic_segment], "body": ""},
            "act3": {"closing": "Keep this on the exec agenda all week.", "cta": cta_payload, "sign_off": "Stay sharp — JunaidQ AI News"},
        }
        return {
            "acts": acts,
            "segments": [basic_segment],
            "headline_blitz": headline_blitz,
            "bridge_sentence": bridge,
            "cta": cta_payload,
        }

    def _compose_opening(self, headlines: List[str]) -> str:
        if not headlines:
            return "Here's the AI briefing execs are trading first thing." 
        if len(headlines) == 1:
            return f"Here's the AI headline shaking boardrooms: {headlines[0]}."
        intro = ", ".join(headlines[:-1])
        return f"Today's AI pulse: {intro}, and {headlines[-1]}."

    def _compose_so_what(self, keyword: str, analysis: Dict[str, Any]) -> str:
        future = analysis["scores"].get("future", 0)
        if future > 0.6:
            return f"Board signal: {keyword.title()} is moving from slideware to deployment this quarter."
        shock = analysis["scores"].get("shock", 0)
        if shock > 0.6:
            return f"Risk alert: this {keyword} twist forces contingency planning now."
        return f"Why it matters: {keyword} just graduated into the main revenue conversation."

    def _compose_now_what(self, keyword: str, analysis: Dict[str, Any]) -> str:
        complexity = analysis.get("technical_complexity")
        if complexity:
            return f"Next move: pair an architecture lead with ops to translate {keyword} into a controlled pilot."
        return f"Next move: brief your go-to-market team on how to position around {keyword}."

    def _compose_closing(self, analyzed: List[Dict[str, Any]]) -> str:
        highlights = [story["analysis"].get("wow_highlight") for story in analyzed[:2] if story["analysis"].get("wow_highlight")]
        if highlights:
            return "Final pulse: " + " ".join(highlights)
        return "Final pulse: the winners are moving faster on AI than the headlines suggest—stay proactive."

    def _aggregate_keywords(self, segments: List[Dict[str, Any]]) -> List[str]:
        keywords: List[str] = []
        for segment in segments:
            for keyword in segment.get("keywords", [])[:3]:
                if keyword not in keywords:
                    keywords.append(keyword)
        return keywords or ["ai", "executive brief"]

    def _fallback_response(self) -> Dict[str, Any]:
        text = (
            "Today in AI: momentum is building across breakthroughs, funding, and governance."
            " Executives should assign owners now and stay sharp."
        )
        return {
            "vo_script": text,
            "lower_thirds": ["AI momentum watch"],
            "broll_keywords": ["ai", "governance", "momentum"],
            "chapters": [],
            "metadata": {
                "validator": {"passed": False, "score": 0.0, "missing": ["stories"]},
                "structure": {},
            },
        }


def generate_script(stories: List[Dict[str, Any]]) -> Dict[str, Any]:
    generator = ScriptGenerator()
    return generator.generate_script(stories)
