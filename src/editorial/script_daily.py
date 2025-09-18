from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

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

_TITLE_SUBJECT_BLOCKLIST = {
    "A",
    "AN",
    "THE",
    "THIS",
    "THAT",
    "THESE",
    "THOSE",
    "HOW",
    "WHY",
    "WHAT",
    "WHEN",
    "WHERE",
    "WHO",
    "WHICH",
    "IS",
    "ARE",
    "CAN",
    "SHOULD",
    "COULD",
    "WOULD",
    "WILL",
    "MAY",
    "MIGHT",
    "DO",
    "DOES",
    "DID",
    "AI",
    "ARTIFICIAL",
    "INTELLIGENCE",
    "BREAKING",
    "LIVE",
    "UPDATE",
    "UPDATES",
    "INSIDE",
    "REPORT",
    "ANALYSIS",
    "NEWS",
    "AUTOMATION",
    "FUNDING",
    "COMPLIANCE",
    "POLICY",
    "REGULATION",
    "GOVERNANCE",
    "GOVERNMENT",
    "MARKET",
    "MARKETS",
    "INVESTMENT",
    "INVESTMENTS",
    "INVESTORS",
    "STRATEGY",
    "STRATEGIES",
    "WORKFLOW",
    "WORKFLOWS",
    "BUSINESS",
    "BUSINESSES",
    "OPERATORS",
    "TREND",
    "TRENDS",
    "OUTLOOK",
    "OUTLOOKS",
    "FORECAST",
    "FORECASTS",
    "BUDGET",
    "BUDGETS",
    "EARNINGS",
}

_WOW_METRIC_PATTERN = re.compile(
    r"(?:[$€£¥]?\d[\d,]*(?:\.\d+)?\s?(?:%|percent|pts|points|million|billion|trillion|bn|m|k|x|times)?)",
    re.IGNORECASE,
)

_DEFAULT_ANALOGY = "Net out the jargon: this unlocks a new capability executives can operationalize if they move fast."


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
            "opening_hook": package["acts"]["act1"]["hook"] + "\n",
            "headline_blitz": "\n".join(f"• {h}" for h in package["headline_blitz"]),
            "bridge_sentence": package["bridge_sentence"] + "\n",
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
                },
                "pacing": package.get("pacing", {}),
                "tone": {"llm_used": tone_result["llm_used"]},
            },
        }
        return output

    def _compose_package(self, analyzed: List[Dict[str, Any]]) -> Dict[str, Any]:
        top_stories = analyzed[:3]
        headline_blitz = self.analyzer.headline_blitz(analyzed, limit=4)
        bridge_sentence = self.analyzer.build_bridge(analyzed)

        segments: List[Dict[str, Any]] = []
        used_analogies: set[str] = set()
        used_transitions: set[str] = set()
        for idx, story in enumerate(top_stories):
            analysis = story["analysis"]
            segment_type = _determine_segment_type(story)
            template = SEGMENT_TEMPLATES.get(segment_type, SEGMENT_TEMPLATES["news"])
            keywords = analysis.get("keywords", [])
            highlight = self._select_highlight(story)
            topic_phrase = self._topic_label(story, highlight)
            impact_profile = self._impact_profile(analysis)
            so_what_text, now_what_text = self._compose_impact_statements(story, highlight, topic_phrase, impact_profile)
            wow_factor = analysis.get("wow_highlight") or self._compose_wow_from_highlight(
                highlight,
                analysis.get("summary_support"),
                topic_phrase,
            )
            analogy_text = self._craft_analogy(story, highlight, used_analogies)
            wow_score = float(analysis.get("wow_score", 0.0) or 0.0)
            wow_tag = "wow_surge" if wow_score >= 0.65 else ("wow_warm" if wow_score >= 0.35 else "wow_calm")
            risk_level = impact_profile["risk_level"]
            action_tag = {
                "threat": "action_defensive",
                "opportunity": "action_offensive",
                "monitor": "action_monitor",
            }.get(risk_level, "action_monitor")
            segment_position_tag = "segment_final" if idx == len(top_stories) - 1 else f"segment_{idx}"
            transition_tag_candidates = [
                segment_type,
                segment_position_tag,
                impact_profile["tone"],
                risk_level,
                wow_tag,
                action_tag,
                "closing" if idx == len(top_stories) - 1 else "momentum",
            ]
            transition_phrase = self.transitions.pick(transition_tag_candidates, used=used_transitions)
            used_transitions.add(transition_phrase)
            rendered = _render_template(template, {
                "headline": story.get("title", ""),
                "what": highlight,
                "so_what": so_what_text,
                "now_what": now_what_text,
                "analogy": analogy_text,
                "wow_factor": wow_factor,
                "transition": transition_phrase,
            })
            segment_words = len(rendered.split())
            segment_duration = round(segment_words / 155 * 60, 1) if segment_words else 0.0
            segments.append({
                "headline": story.get("title", ""),
                "what": highlight,
                "so_what": so_what_text,
                "now_what": now_what_text,
                "analogy": analogy_text,
                "wow_factor": wow_factor,
                "transition": transition_phrase,
                "keywords": keywords,
                "segment_type": segment_type,
                "topic_phrase": topic_phrase,
                "impact_profile": impact_profile,
                "estimated_duration": segment_duration,
                "word_count": segment_words,
                "rendered": rendered,
            })

        cta_topic = segments[0]["topic_phrase"] if segments else "AI initiative"
        cta_payload = self.cta.generate(
            cta_topic,
            context=self._build_cta_context(segments[0] if segments else None)
        )

        total_words = sum(segment["word_count"] for segment in segments)
        total_duration = round(sum(segment["estimated_duration"] for segment in segments), 1)
        avg_segment_duration = round(total_duration / max(1, len(segments)), 1)

        acts = {
            "act1": {
                "hook": self._compose_opening(headline_blitz),
                "bridge": bridge_sentence,
            },
            "act2": {
                "segments": segments,
                "body": "",
                "duration_estimate": total_duration,
                "word_count": total_words,
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
            "pacing": {
                "total_seconds": total_duration,
                "average_segment_seconds": avg_segment_duration,
                "segment_estimates": [segment["estimated_duration"] for segment in segments],
            },
        }

    def _select_highlight(self, story: Dict[str, Any]) -> str:
        analysis = story.get("analysis", {})
        title = str(story.get("title", "")).strip()
        candidates = [
            analysis.get("summary_highlight"),
            analysis.get("summary_support"),
            analysis.get("wow_highlight"),
            _first_sentence(story.get("summary"), title),
        ]
        for value in candidates:
            if value:
                text = str(value).strip()
                if text:
                    if text.lower() == title.lower():
                        text = self._synthetic_highlight(story, analysis)
                    return text if text.endswith(tuple(".!?")) else text + "."
        fallback = self._synthetic_highlight(story, analysis)
        return fallback if fallback.endswith(tuple(".!?")) else fallback + "."

    def _synthetic_highlight(self, story: Dict[str, Any], analysis: Dict[str, Any]) -> str:
        impact_profile = self._impact_profile(analysis)
        risk = impact_profile.get("risk_level", "monitor")
        keywords = analysis.get("keywords", [])
        key_term = next((k for k in keywords if len(k) > 3), "AI move")
        profile = self._subject_profile(story)
        subject = profile["label"]
        actor = subject or "Exec teams"
        plural = profile["is_plural"] if subject else True
        if risk == "threat":
            verb_are = "are" if plural else "is"
            return f"{actor} {verb_are} staring at a {key_term} risk that could derail the quarter"
        if risk == "opportunity":
            return f"{actor} can convert this {key_term} surge into an early edge"
        verb_are = "are" if plural else "is"
        return f"{actor} {verb_are} watching this {key_term} signal harden into the next KPI"

    def _topic_label(self, story: Dict[str, Any], highlight: str) -> str:
        analysis = story.get("analysis", {})
        keywords = analysis.get("keywords", [])
        key_term = next((k for k in keywords if len(k) > 3), "AI move")
        descriptor_map = {
            "ban": "regulatory squeeze",
            "delay": "JV delay",
            "launch": "launch window",
            "raise": "capital raise",
            "funding": "funding momentum",
            "merger": "deal pressure",
            "partnership": "partnership expansion",
            "jobs": "workforce shock",
            "safety": "safety mandate",
            "pilot": "pilot window",
            "surge": "spending surge",
            "stock": "valuation swing",
        }
        descriptor_core = descriptor_map.get(key_term.lower(), key_term)
        descriptor = descriptor_core.strip()
        if descriptor:
            descriptor = descriptor[0].upper() + descriptor[1:]
        if len(descriptor.split()) > 12:
            descriptor = " ".join(descriptor.split()[:12]) + "…"
        return descriptor

    def _impact_profile(self, analysis: Dict[str, Any]) -> Dict[str, str]:
        scores = analysis.get("scores", {})
        shock = scores.get("shock", 0.0)
        future = scores.get("future", 0.0)
        if shock >= 0.55:
            return {"risk_level": "threat", "tone": "alert"}
        if future >= 0.55:
            return {"risk_level": "opportunity", "tone": "momentum"}
        return {"risk_level": "monitor", "tone": "signal"}

    def _compose_impact_statements(
        self,
        story: Dict[str, Any],
        _highlight: str,
        topic_phrase: str,
        impact_profile: Dict[str, str],
    ) -> tuple[str, str]:
        subject_profile = self._subject_profile(story)
        subject = subject_profile["label"]
        actor = subject or "Exec teams"
        plural = subject_profile["is_plural"] if subject else True
        risk_level = impact_profile["risk_level"]
        topic_for_sentence = topic_phrase.rstrip(".")
        if risk_level == "threat":
            verb_face = "face" if plural else "faces"
            so_text = f"Board alert: {actor} {verb_face} {topic_for_sentence} tipping into the headline risk."
            now_text = f"Action: convene legal, finance, and ops this week to scenario-plan around {topic_for_sentence}."
        elif risk_level == "opportunity":
            so_text = f"Opportunity signal: {actor} can turn {topic_for_sentence} into a first-mover edge."
            now_text = f"Action: assign a tiger team to prototype {topic_for_sentence} before rivals lock budgets."
        else:
            verb_are = "are" if plural else "is"
            so_text = f"Strategic watch: {actor} {verb_are} watching {topic_for_sentence} become the next boardroom talking point."
            now_text = f"Action: instrument metrics and nominate an owner to monitor outcomes over the next sprint."
        return so_text, now_text

    def _compose_wow_from_highlight(self, highlight: str, support: Optional[str], topic_phrase: str) -> str:
        for candidate in (support, highlight):
            snippet = self._wow_snippet(candidate, topic_phrase)
            if snippet:
                return snippet
        base = highlight.rstrip(".")
        return f"Wow signal: {base}."

    def _wow_snippet(self, text: Optional[str], topic_phrase: str) -> Optional[str]:
        if not text:
            return None
        sentences = re.split(r"(?<=[.!?])\s+", str(text).strip())
        for sentence in sentences:
            cleaned = sentence.strip()
            if not cleaned:
                continue
            if _WOW_METRIC_PATTERN.search(cleaned) or '"' in cleaned:
                return self._format_wow_sentence(cleaned, topic_phrase)
        return None

    def _format_wow_sentence(self, sentence: str, topic_phrase: str) -> str:
        stripped = sentence.strip().rstrip(".!?")
        lowered = stripped.lower()
        for article in ("a ", "an ", "the "):
            if lowered.startswith(article):
                stripped = stripped[len(article):]
                lowered = stripped.lower()
                break
        prefix = ""
        if not lowered.startswith(("that ", "this ", "these ", "those ")):
            prefix = "That "
        core = stripped
        if prefix and core:
            if core[:2].isupper():
                pass
            elif core[0].isupper():
                core = core[0].lower() + core[1:]
        if _WOW_METRIC_PATTERN.search(sentence) or '"' in sentence:
            return f"{prefix}{core} — {self._wow_suffix(topic_phrase)}"
        return f"{prefix}{core}."

    def _wow_suffix(self, topic_phrase: str) -> str:
        topic = topic_phrase.rstrip(".").strip()
        if not topic:
            return "that's the board-level jolt this quarter."
        normalized = topic.lower()
        variants = [
            f"that's the board-level jolt around {normalized}.",
            f"that's the signal exec teams will brief under {normalized}.",
            f"that's why {normalized} just jumped on the board docket.",
        ]
        index = abs(hash(normalized)) % len(variants)
        return variants[index]

    def _craft_analogy(self, story: Dict[str, Any], highlight: str, used: set[str]) -> str:
        analysis = story.get("analysis", {})
        candidate = (analysis.get("analogy") or "").strip()
        if candidate and candidate not in used and candidate != _DEFAULT_ANALOGY:
            used.add(candidate)
            return candidate
        llm_candidate = self._llm_analogy(story, highlight)
        if llm_candidate and llm_candidate not in used:
            used.add(llm_candidate)
            return llm_candidate
        improvised = self._improvise_analogy(story, highlight, used)
        used.add(improvised)
        return improvised

    def _improvise_analogy(self, story: Dict[str, Any], highlight: str, used: set[str]) -> str:
        analysis = story.get("analysis", {})
        keywords = [k.lower() for k in analysis.get("keywords", []) if k]
        theme_text = " ".join(keywords + highlight.lower().split())
        palette = [
            ({"delay", "compliance", "governance", "regulation"}, [
                "It's the red light forcing the convoy to redraw the route before the bridge closes.",
                "It's the compliance fire drill you run before auditors ring the bell.",
                "It's the policy siren that tells treasury to spin up contingency playbooks." 
            ]),
            ({"launch", "product", "rollout", "pilot"}, [
                "It's the launch countdown that snaps every squad into the same war room.",
                "It's the dress rehearsal that turns the beta floor into mission control.",
                "It's the runway light that says wheels up now or never." 
            ]),
            ({"ban", "restriction", "halt"}, [
                "It's like a regulator slamming the emergency brake while you're still accelerating.",
                "It's the red card that benches your star player mid-match.",
                "It's the safety lock engaging while ops are still mid-sprint." 
            ]),
            ({"jobs", "talent", "hiring", "labor"}, [
                "Treat it like a labour negotiation dry-run before the unions walk in.",
                "It's the talent draft where you either show up ready or lose the season.",
                "It's HR's hurricane drill—close the loops now or clean up later." 
            ]),
            ({"safety", "alignment", "trust", "ethics"}, [
                "It's the compliance fire drill you run before auditors walk the floor.",
                "It's the seatbelt check right before the rocket fire sequence.",
                "It's the guardrail inspection that happens before the convoy hits mountain roads." 
            ]),
            ({"automation", "workflow", "process"}, [
                "It's the robotics upgrade that frees frontline teams for the next play.",
                "It's the ops autopilot that lets leadership watch dashboards instead of dials.",
                "It's the process rewire that turns lag into same-day action." 
            ]),
            ({"funding", "raise", "capital", "investment"}, [
                "Think of it as venture fuel—volatile, loud, and capable of powering a breakout.",
                "It's the late-night wire transfer that decides who ships first next quarter.",
                "It's the capital cannon shot that rattles every rival's budget room." 
            ]),
            ({"competition", "race", "rival", "market"}, [
                "It's the pace car suddenly gunning it—you either draft or get dropped.",
                "It's the sprint finish where every stride decides the podium.",
                "It's the war-room chess move that flips the board in one play." 
            ]),
            ({"infrastructure", "compute", "chip", "capacity", "latency"}, [
                "It's the data center crank-up that feels like adding new lanes to the freeway overnight.",
                "It's the turbocharger bolted onto an engine already redlining.",
                "It's laying fresh fiber just as the trading floor opens." 
            ]),
            ({"security", "breach", "risk", "threat"}, [
                "It's the smoke alarm chirp you heed before the fire marshal shows up.",
                "It's the pen-test siren telling ops to lock the vault now.",
                "It's the intrusion drill where seconds decide the cleanup bill." 
            ]),
            ({"partnership", "merger", "deal"}, [
                "It's the handshake that reshuffles the league brackets overnight.",
                "It's the joint venture whiteboard that redraws the supply map.",
                "It's the deal memo that turns rivals into an expedition team." 
            ]),
        ]

        for triggers, phrases in palette:
            if any(term in theme_text for term in triggers):
                for phrase in phrases:
                    if phrase not in used:
                        return phrase

        focus_fragment = self._analogy_focus(highlight)
        templates = [
            "It's the war-room brief that tells leaders the {} shift just changed the board agenda.",
            "Think of it as the {} sprint compressed into 48 hours.",
            "It's the early-warning radar ping hinting the {} move is the next board slide.",
            "It's the pit-stop where the {} machine gets rebuilt before the race restarts.",
        ]
        for offset in range(len(templates)):
            idx = (abs(hash(focus_fragment)) + offset) % len(templates)
            candidate = templates[idx].format(focus_fragment)
            if candidate not in used:
                return candidate

        # Deterministic final fallback ensures we always return a phrase.
        return "It's the brief from the war room telling you the map just changed."

    def _analogy_focus(self, highlight: str) -> str:
        cleaned = re.sub(r"[^a-zA-Z0-9%$\s]", "", highlight).strip()
        if not cleaned:
            return "this move"
        stopwords = {
            "and",
            "are",
            "is",
            "the",
            "that",
            "this",
            "these",
            "those",
            "for",
            "with",
            "into",
            "onto",
            "about",
            "around",
            "over",
            "under",
            "just",
            "now",
            "today",
            "after",
            "before",
            "while",
            "as",
            "by",
            "to",
            "of",
            "from",
        }
        tokens: List[str] = []
        for raw in cleaned.split():
            lower = raw.lower()
            if lower in stopwords:
                continue
            tokens.append(raw if raw.isupper() else lower)
            if len(tokens) >= 4:
                break
        if not tokens:
            return "this move"
        return " ".join(tokens)

    def _llm_analogy(self, story: Dict[str, Any], highlight: str) -> Optional[str]:
        api_key = getattr(settings, "OPENAI_API_KEY", None)
        if not api_key:
            return None
        try:
            from openai import OpenAI  # type: ignore
        except Exception:
            return None

        prompt = (
            "Craft a single-sentence, witty analogy (max 28 words) for an executive AI briefing. "
            "Avoid colons, keep it business-relevant, and do not repeat prior analogies.\n"
            f"Headline: {story.get('title', '')}\n"
            f"Highlight: {highlight}\n"
        )

        model = os.getenv("ANALOGY_MODEL", "gpt-4o-mini")
        try:
            client = OpenAI(api_key=api_key)
            try:
                response = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You craft sharp, vivid analogies for executive briefings."},
                        {"role": "user", "content": prompt},
                    ],
                    max_tokens=80,
                    temperature=0.7,
                )
                message = response.choices[0].message
                text_content = message.get("content", "") if isinstance(message, dict) else getattr(message, "content", "")
                if isinstance(text_content, list):
                    collected: List[str] = []
                    for part in text_content:
                        if isinstance(part, dict):
                            collected.append(str(part.get("text", "")))
                        else:
                            collected.append(str(part))
                    text = "".join(collected).strip()
                else:
                    text = str(text_content).strip()
            except AttributeError:
                structured = client.responses.create(
                    model=model,
                    input=[{"role": "user", "content": [{"type": "text", "text": prompt}]}],
                    max_output_tokens=80,
                )
                text = structured.output[0].content[0].text.strip()
        except Exception:
            return None

        if not text:
            return None
        normalized = text.rstrip(".!?") + "."
        return normalized

    def _subject_profile(self, story: Dict[str, Any]) -> Dict[str, Any]:
        analysis = story.get("analysis", {})
        companies = story.get("companies_mentioned") or analysis.get("companies") or []
        cleaned: List[str] = []
        for raw in companies:
            text = str(raw).strip()
            if text and text not in cleaned:
                cleaned.append(text)
        if cleaned:
            label = cleaned[0] if len(cleaned) == 1 else " & ".join(cleaned[:2])
            is_plural = len(cleaned) > 1 or bool(re.search(r"(&| and )", label))
            return {"label": label, "is_plural": is_plural}

        title = str(story.get("title", ""))
        title_main = title.split(" - ")[0]
        matches = re.findall(r"\b([A-Z][A-Za-z0-9&]+(?:\s+[A-Z][A-Za-z0-9&]+)*)\b", title_main)
        for match in matches:
            candidate = match.strip()
            if not candidate:
                continue
            if candidate.upper() in _TITLE_SUBJECT_BLOCKLIST:
                continue
            label = candidate
            is_plural = bool(re.search(r"(&| and )", label))
            return {"label": label, "is_plural": is_plural}

        return {"label": None, "is_plural": True}

    def _primary_subject(self, story: Dict[str, Any]) -> Optional[str]:
        return self._subject_profile(story)["label"]

    def _build_cta_context(self, segment: Optional[Dict[str, Any]]) -> Optional[Dict[str, str]]:
        if not segment:
            return None
        impact = segment.get("impact_profile", {})
        action_text = segment.get("now_what", "")
        normalized_action = self._normalize_action(action_text)
        return {
            "risk_level": impact.get("risk_level", "monitor"),
            "highlight": segment.get("what", ""),
            "action": normalized_action,
        }

    def _normalize_action(self, text: str) -> str:
        if not text:
            return ""
        stripped = text.strip()
        if stripped.lower().startswith("action:"):
            stripped = stripped.split(":", 1)[1].strip()
        return stripped.rstrip(".")

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
            "estimated_duration": 0.0,
            "word_count": 0,
        }
        template = SEGMENT_TEMPLATES["news"]
        render_values = {}
        for key, value in basic_segment.items():
            if key in {"keywords", "segment_type", "estimated_duration", "word_count"}:
                continue
            render_values[key] = value
        basic_segment["rendered"] = _render_template(template, render_values)
        basic_segment["word_count"] = len(basic_segment["rendered"].split())
        basic_segment["estimated_duration"] = round(basic_segment["word_count"] / 155 * 60, 1) if basic_segment["word_count"] else 0.0
        headline_blitz = [basic_segment["headline"]]
        bridge = "Every signal points to AI budgets accelerating despite governance anxiety."
        cta_payload = self.cta.generate(basic_segment["keywords"][0] if basic_segment["keywords"] else "AI strategy")
        acts = {
            "act1": {"hook": f"Today in AI: {basic_segment['headline']}", "bridge": bridge},
            "act2": {"segments": [basic_segment], "body": "", "duration_estimate": basic_segment["estimated_duration"], "word_count": basic_segment["word_count"]},
            "act3": {"closing": "Keep this on the exec agenda all week.", "cta": cta_payload, "sign_off": "Stay sharp — JunaidQ AI News"},
        }
        return {
            "acts": acts,
            "segments": [basic_segment],
            "headline_blitz": headline_blitz,
            "bridge_sentence": bridge,
            "cta": cta_payload,
            "pacing": {
                "total_seconds": basic_segment["estimated_duration"],
                "average_segment_seconds": basic_segment["estimated_duration"],
                "segment_estimates": [basic_segment["estimated_duration"]],
            },
        }

    def _compose_opening(self, headlines: List[str]) -> str:
        if not headlines:
            return "Here's the AI briefing execs are trading first thing." 
        if len(headlines) == 1:
            return f"Here's the AI headline shaking boardrooms: {headlines[0]}."
        intro = ", ".join(headlines[:-1])
        return f"Today's AI pulse: {intro}, and {headlines[-1]}."

    def _compose_closing(self, analyzed: List[Dict[str, Any]]) -> str:
        snippets: List[str] = []
        for story in analyzed[:2]:
            analysis = story.get("analysis", {})
            for key in ("summary_support", "wow_highlight", "summary_highlight"):
                value = analysis.get(key)
                if value:
                    snippets.append(str(value).rstrip("."))
                    break
        if snippets:
            joined = " ".join(snippets[:2])
            return f"Final pulse: {joined}."
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
