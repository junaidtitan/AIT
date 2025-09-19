"""Tests for LangGraph helpers."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.graphs.nodes.mergers import merge_and_dedupe
from src.graphs.state import ResearchState
from src.models import StoryInput, StorySource
from src.editorial.script_adapter import generate_script_draft


def test_merge_and_dedupe_removes_duplicates():
    source = StorySource(name="Test", url="https://example.com/feed")
    story_a = StoryInput(source=source, title="Example", url="https://example.com/a")
    story_b = StoryInput(source=source, title="Example", url="https://example.com/a")
    state = ResearchState(raw_stories=[story_a, story_b])
    result = merge_and_dedupe(state)
    assert len(result.raw_stories) == 1


def test_generate_script_draft_produces_text():
    stories = [
        {
            "title": "OpenAI ships GPT-5 with enterprise guardrails",
            "summary": "OpenAI announces GPT-5 with major safety upgrades.",
            "url": "https://example.com/gpt5",
            "source_domain": "openai.com",
            "category": "news",
            "full_text": "OpenAI released GPT-5 with expanded capabilities.",
        }
    ]
    draft = generate_script_draft(stories)
    assert draft.final_text
    assert draft.validation.score >= 0
