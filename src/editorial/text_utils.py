"""Utilities for cleaning and normalising article text."""

from __future__ import annotations

import html
import re
from typing import Iterable, Optional

from bs4 import BeautifulSoup


_NOISE_PATTERNS: Iterable[re.Pattern[str]] = (
    re.compile(r"bibtex formatted citation", re.IGNORECASE),
    re.compile(r"^\s*export citation", re.IGNORECASE),
    re.compile(r"^\s*cite (this|article)", re.IGNORECASE),
    re.compile(r"click to (share|print)", re.IGNORECASE),
    re.compile(r"share this (story|article)", re.IGNORECASE),
)

_ARXIV_HEADER = re.compile(
    r"^arxiv:\S+(?:\s+announce type:\s*\w+)?\s+abstract:\s*",
    re.IGNORECASE,
)


def _strip_noise_sentences(text: str) -> str:
    """Remove boilerplate sentences that confuse downstream stages."""
    if not text:
        return ""

    segments = re.split(r"(?<=[.!?])\s+", text)
    cleaned_segments: list[str] = []

    for segment in segments:
        normalized = segment.strip()
        if not normalized:
            continue

        if any(pattern.search(normalized) for pattern in _NOISE_PATTERNS):
            continue

        cleaned_segments.append(normalized)

    return " ".join(cleaned_segments)


def clean_text(value: Optional[str]) -> str:
    """Strip HTML tags, decode entities, drop boilerplate, and collapse whitespace."""
    if not value:
        return ""

    decoded = html.unescape(value)
    soup = BeautifulSoup(decoded, "html.parser")
    text = soup.get_text(" ", strip=True)
    no_padding = " ".join(text.split())
    no_padding = _ARXIV_HEADER.sub("", no_padding)

    # Ensure ArXiv abstracts start with a proper subject
    # If the text starts with a verb (common in ArXiv), prepend "This paper"
    cleaned = _strip_noise_sentences(no_padding)
    if cleaned:
        # Check if it starts with a verb (introduces, presents, proposes, etc.)
        first_word = cleaned.split()[0].lower() if cleaned.split() else ""
        verb_starters = ['introduces', 'presents', 'proposes', 'describes', 'demonstrates',
                        'develops', 'explores', 'investigates', 'examines', 'analyzes',
                        'discusses', 'addresses', 'provides', 'offers', 'shows']
        if first_word in verb_starters:
            cleaned = f"This paper {cleaned[0].lower()}{cleaned[1:]}"

    return cleaned


__all__ = ["clean_text"]