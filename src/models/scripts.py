"""Script and editorial models for LangGraph Stage 2."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ValidationReport(BaseModel):
    """Result of validating a generated script."""

    passed: bool
    score: float
    missing: List[str] = Field(default_factory=list)
    severity: str = "info"
    metrics: Dict[str, Any] = Field(default_factory=dict)
    recommended_actions: List[str] = Field(default_factory=list)


class SegmentDraft(BaseModel):
    """Single narrative segment used for video assembly."""

    headline: str
    what: str
    so_what: str
    now_what: str
    analogy: str
    wow_factor: str
    transition: str
    keywords: List[str] = Field(default_factory=list)
    segment_type: str = "news"
    topic_phrase: Optional[str] = None
    impact_profile: Dict[str, Any] = Field(default_factory=dict)
    voiceover: Optional[str] = None
    duration_seconds: float = 0.0
    word_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ScriptDraft(BaseModel):
    """Structured script artifact emitted by the script generator."""

    created_at: datetime = Field(default_factory=datetime.utcnow)
    title: Optional[str] = None
    headline_blitz: List[str] = Field(default_factory=list)
    bridge_sentence: Optional[str] = None
    segments: List[SegmentDraft] = Field(default_factory=list)
    acts: Dict[str, Any] = Field(default_factory=dict)
    cta: Dict[str, Any] = Field(default_factory=dict)
    pacing: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    validation: ValidationReport = Field(default_factory=lambda: ValidationReport(passed=False, score=0.0))
    final_text: Optional[str] = None

    def total_duration(self) -> float:
        return sum(segment.duration_seconds for segment in self.segments)

    def total_words(self) -> int:
        return sum(segment.word_count for segment in self.segments)


class PipelineDiagnostics(BaseModel):
    """Lightweight logging container passed through LangGraph state."""

    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    events: List[Dict[str, Any]] = Field(default_factory=list)

    def record(self, level: str, message: str, **details: Any) -> None:
        payload = {"level": level, "message": message, **details}
        self.events.append(payload)
        if level == "error":
            self.errors.append(message)
        elif level == "warning":
            self.warnings.append(message)


__all__ = [
    "ValidationReport",
    "SegmentDraft",
    "ScriptDraft",
    "PipelineDiagnostics",
]
