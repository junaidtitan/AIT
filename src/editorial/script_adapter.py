"""Adapter between legacy script generator and typed LangGraph models."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List

from src.editorial.script_daily import ScriptGenerator
from src.editorial.structure_validator import StructureValidator
from src.models import SegmentDraft, ScriptDraft, ValidationReport


def _ensure_dicts(stories: Iterable[Any]) -> List[Dict[str, Any]]:
    payload: List[Dict[str, Any]] = []
    for story in stories:
        if hasattr(story, "model_dump"):
            payload.append(story.model_dump())
        else:
            payload.append(dict(story))
    return payload


def _build_segments(structure: Dict[str, Any], pacing: Dict[str, Any]) -> List[SegmentDraft]:
    segments: List[SegmentDraft] = []
    raw_segments = structure.get("segments", [])
    duration_estimates = pacing.get("segment_estimates", []) if isinstance(pacing, dict) else []
    for idx, segment in enumerate(raw_segments):
        duration = float(duration_estimates[idx]) if idx < len(duration_estimates) else float(segment.get("estimated_duration", 0.0))
        word_count = int(segment.get("word_count", 0))
        segments.append(
            SegmentDraft(
                headline=segment.get("headline", ""),
                what=segment.get("what", ""),
                so_what=segment.get("so_what", ""),
                now_what=segment.get("now_what", ""),
                analogy=segment.get("analogy", ""),
                wow_factor=segment.get("wow_factor", ""),
                transition=segment.get("transition", ""),
                keywords=list(segment.get("keywords", [])),
                segment_type=segment.get("segment_type", "news"),
                topic_phrase=segment.get("topic_phrase"),
                impact_profile=dict(segment.get("impact_profile", {})),
                voiceover=segment.get("rendered"),
                duration_seconds=duration,
                word_count=word_count,
                metadata={k: v for k, v in segment.items() if k not in {"headline", "what", "so_what", "now_what", "analogy", "wow_factor", "transition", "keywords", "segment_type", "topic_phrase", "impact_profile", "rendered", "estimated_duration", "word_count"}},
            )
        )
    return segments


def generate_script_draft(stories: Iterable[Any]) -> ScriptDraft:
    generator = ScriptGenerator()
    raw_payload = _ensure_dicts(stories)
    legacy = generator.generate_script(raw_payload)
    metadata = legacy.get("metadata", {})
    structure = metadata.get("structure", {})
    pacing = metadata.get("pacing", {})
    segments = _build_segments(structure, pacing)
    validator = StructureValidator()
    validation_payload = {
        "acts": structure.get("acts", {}),
        "segments": structure.get("segments", []),
        "cta": structure.get("cta"),
        "headline_blitz": structure.get("headline_blitz"),
        "bridge_sentence": structure.get("bridge_sentence"),
        "pacing": pacing,
    }
    validation = validator.validate(validation_payload)
    draft = ScriptDraft(
        headline_blitz=list(structure.get("headline_blitz", [])),
        bridge_sentence=structure.get("bridge_sentence"),
        segments=segments,
        acts=structure.get("acts", {}),
        cta=structure.get("cta", {}),
        pacing=pacing if isinstance(pacing, dict) else {},
        metadata={k: v for k, v in metadata.items() if k != "structure"},
        validation=validation,
        final_text=legacy.get("vo_script"),
    )
    return draft


def draft_to_legacy(draft: ScriptDraft) -> Dict[str, Any]:
    lower_thirds = [segment.headline for segment in draft.segments]
    broll_keywords = []
    for segment in draft.segments:
        for keyword in segment.keywords:
            if keyword not in broll_keywords:
                broll_keywords.append(keyword)
    return {
        "vo_script": draft.final_text or "",
        "lower_thirds": lower_thirds,
        "broll_keywords": broll_keywords,
        "chapters": [],
        "metadata": {
            "validator": draft.validation.model_dump(),
            "structure": {
                "segments": [segment.model_dump() for segment in draft.segments],
                "cta": draft.cta,
                "headline_blitz": draft.headline_blitz,
                "bridge_sentence": draft.bridge_sentence,
                "acts": draft.acts,
            },
            "pacing": draft.pacing,
        },
    }
