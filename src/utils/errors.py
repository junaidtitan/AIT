"""Exception hierarchy shared by LangGraph pipeline stages."""

from __future__ import annotations

from typing import Any, Dict, Optional


class StageFailure(RuntimeError):
    """Base exception for failures inside LangGraph stages."""

    payload: Dict[str, Any]

    def __init__(self, message: str, *, payload: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.payload = payload or {}


class FetchTimeout(StageFailure):
    """Raised when an upstream content fetch exceeds its deadline."""


class ValidationFailure(StageFailure):
    """Raised when validation fails and automated regeneration cannot recover."""


__all__ = ["StageFailure", "FetchTimeout", "ValidationFailure"]
