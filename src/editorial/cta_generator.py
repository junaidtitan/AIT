from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Dict, List, Optional

TEMPLATE_PATH = Path(__file__).resolve().parents[2] / "templates" / "cta_patterns.json"


class CTAGenerator:
    """Generate context-aware CTA questions from pattern library."""

    def __init__(self) -> None:
        with open(TEMPLATE_PATH, "r", encoding="utf-8") as handle:
            self._patterns = json.load(handle)

    def generate(
        self,
        topic: str,
        *,
        intent: str | None = None,
        context: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        choices: List[Dict[str, str]] = list(self._patterns)
        if intent:
            filtered = [p for p in choices if intent in p.get("id", "")]
            if filtered:
                choices = filtered

        risk_level = "monitor"
        insight = ""
        action = ""
        if context:
            risk_level = context.get("risk_level", "monitor")
            insight = context.get("highlight", "")
            action = context.get("action", "")
            if risk_level == "threat":
                preferred_ids = {"risk_readiness", "policy_watch", "resilience", "ethics_signal"}
            elif risk_level == "opportunity":
                preferred_ids = {"allocation_decision", "experiment_velocity", "competitive_response", "data_strategy"}
            else:
                preferred_ids = {"customer_obligation", "data_strategy", "talent_gap"}
            filtered = [p for p in choices if p.get("id") in preferred_ids]
            if filtered:
                choices = filtered

        if not choices:
            choices = list(self._patterns)

        pattern = random.choice(choices)
        topic_phrase = topic.strip()
        question_template = pattern.get("pattern", "{{topic}}")
        question = self._fill_pattern(question_template, topic_phrase, insight)
        follow_up = self._compose_follow_up(action, risk_level)
        rendered = self._finalize_question(question, follow_up)
        return {"id": pattern.get("id", "custom"), "question": rendered}

    def _fill_pattern(self, template: str, topic: str, insight: str) -> str:
        question = template.replace("{{topic}}", topic)
        if "{{insight}}" in question:
            effective_insight = self._prepare_insight(insight, topic)
            question = question.replace("{{insight}}", effective_insight)
        # Clean up any stray placeholders
        question = question.replace("{{insight}}", "").strip()
        return " ".join(question.split())

    def _compose_follow_up(self, action: str, risk_level: str) -> str:
        action_core = action.strip()
        if not action_core:
            return ""
        lower_core = action_core[0].lower() + action_core[1:] if action_core else action_core
        if risk_level == "threat":
            clause = lower_core if lower_core.startswith("we ") else f"we {lower_core}"
            return f"Who is accountable for ensuring {clause} before the risk spikes?"
        if risk_level == "opportunity":
            return f"Which leader clears the runway so that the plan to {lower_core} actually happens?"
        clause = lower_core if lower_core.startswith("we ") else f"we {lower_core}"
        return f"Who will own the weekly check that {clause} stays on track?"

    def _finalize_question(self, base: str, follow_up: str) -> str:
        core = base.strip()
        if not core.endswith("?"):
            core = core.rstrip(".") + "?"
        if follow_up:
            return f"{core} {follow_up}".strip()
        return core

    def _prepare_insight(self, insight: str, fallback: str) -> str:
        candidate = insight.strip()
        if not candidate:
            candidate = fallback
        lowered = candidate.lower()
        for original, replacement in (("a ", "a "), ("an ", "an "), ("the ", "the ")):
            if lowered.startswith(original):
                candidate = replacement + candidate[len(original):]
                break
        return candidate.rstrip(".")


__all__ = ["CTAGenerator"]
