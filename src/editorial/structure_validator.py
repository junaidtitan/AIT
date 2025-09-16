from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

_REQUIRED_ACTS = {"act1", "act2", "act3"}
_SEGMENT_FIELDS = {"headline", "what", "so_what", "now_what", "analogy", "wow_factor", "transition"}


@dataclass
class ValidationResult:
    passed: bool
    score: float
    missing: List[str]


class StructureValidator:
    """Ensure generated scripts meet the futurist structure requirements."""

    def validate(self, payload: Dict[str, object]) -> ValidationResult:
        missing: List[str] = []
        score = 1.0

        acts = payload.get("acts")
        if not isinstance(acts, dict):
            missing.append("acts")
            return ValidationResult(False, 0.0, missing)

        for act in _REQUIRED_ACTS:
            if act not in acts or not acts[act]:
                missing.append(f"act:{act}")
                score -= 0.2

        segments = payload.get("segments")
        if not isinstance(segments, list) or not segments:
            missing.append("segments")
            score -= 0.4
        else:
            for idx, segment in enumerate(segments):
                for field in _SEGMENT_FIELDS:
                    if not (isinstance(segment, dict) and segment.get(field)):
                        missing.append(f"segment_{idx}:{field}")
                        score -= 0.05

        cta = payload.get("cta")
        if not cta:
            missing.append("cta")
            score -= 0.2

        if payload.get("headline_blitz"):
            pass
        else:
            missing.append("headline_blitz")
            score -= 0.1

        if payload.get("bridge_sentence"):
            pass
        else:
            missing.append("bridge_sentence")
            score -= 0.05

        score = max(0.0, min(1.0, score))
        return ValidationResult(not missing, score, missing)


__all__ = ["StructureValidator", "ValidationResult"]
