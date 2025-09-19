"""Utilities for canonicalising content metadata across ingestion stages."""

from __future__ import annotations

import re
from typing import Iterable, List
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import xxhash

_TRACKING_PARAMS = {
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "utm_term",
    "utm_content",
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
}

_WHITESPACE_RE = re.compile(r"\s+")


def canonical_url(url: str | None) -> str | None:
    """Return a URL with tracking parameters stripped and lowercase scheme."""
    if not url:
        return None
    try:
        parsed = urlparse(url)
        query_items = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True) if k not in _TRACKING_PARAMS]
        cleaned_query = urlencode(query_items)
        new_parts = (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path or "",
            parsed.params or "",
            cleaned_query,
            parsed.fragment or "",
        )
        return urlunparse(new_parts)
    except ValueError:
        return url


def content_fingerprint(*parts: str) -> str:
    """Create a stable hash used for dedupe and checkpointing."""
    normalised = "\u0001".join(normalize_text(part) for part in parts if part)
    return xxhash.xxh3_64_hexdigest(normalised)


def normalize_text(text: str | None) -> str:
    if not text:
        return ""
    text = _WHITESPACE_RE.sub(" ", text)
    return text.strip()


def merge_keywords(*collections: Iterable[str]) -> List[str]:
    """Merge keyword collections while keeping order and uniqueness."""
    seen: set[str] = set()
    merged: List[str] = []
    for collection in collections:
        for item in collection:
            value = normalize_text(item).lower()
            if not value or value in seen:
                continue
            seen.add(value)
            merged.append(value)
    return merged


__all__ = ["canonical_url", "content_fingerprint", "normalize_text", "merge_keywords"]
