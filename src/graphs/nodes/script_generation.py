"""Script generation nodes for LangGraph Stage 2."""

from __future__ import annotations

from src.editorial.script_adapter import draft_to_legacy, generate_script_draft
from src.graphs.state import ScriptState


def prepare_story_payload(state: ScriptState) -> ScriptState:
    if not state.selected_stories:
        state.errors.append("no_selected_stories")
        state.metadata["manual_review_required"] = True
        state.manual_review = True
        return state
    state.analysis["stories_payload"] = [story.model_dump() for story in state.selected_stories]
    state.attempts = 0
    state.metadata.setdefault("max_attempts", 2)
    return state


def generate_script(state: ScriptState) -> ScriptState:
    payload = state.analysis.get("stories_payload", [])
    state.attempts += 1
    draft = generate_script_draft(payload)
    state.draft = draft
    state.final_script = None
    state.validation = draft.validation.model_dump()
    state.metadata["legacy_output"] = draft_to_legacy(draft)
    state.metadata["validation"] = draft.validation.model_dump()
    state.diagnostics.record(
        "info",
        "script_generated",
        attempt=state.attempts,
        score=draft.validation.score,
    )
    if not draft.validation.passed:
        missing = list(dict.fromkeys(draft.validation.missing))
        state.errors.extend(err for err in missing if err not in state.errors)
    else:
        state.final_script = draft
    return state


def assess_script(state: ScriptState) -> str:
    draft = state.draft
    if draft and draft.validation.passed:
        state.final_script = draft
        return "accept"

    max_attempts = int(state.metadata.get("max_attempts", 2))
    if state.attempts < max_attempts:
        return "retry"

    state.metadata["manual_review_required"] = True
    state.manual_review = True
    return "manual"


def mark_manual_review(state: ScriptState) -> ScriptState:
    state.metadata["manual_review_required"] = True
    state.manual_review = True
    if state.final_script is None and state.draft is not None:
        state.final_script = state.draft
    state.diagnostics.record(
        "warning",
        "manual_review",
        attempts=state.attempts,
        errors=list(state.errors),
    )
    return state


def finalize_script(state: ScriptState) -> ScriptState:
    if state.final_script is None and state.draft is not None:
        state.final_script = state.draft
    state.metadata["attempts"] = state.attempts
    return state
