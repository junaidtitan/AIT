"""Async helper utilities shared by LangGraph nodes."""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, Iterable, List, Sequence, TypeVar

import anyio
from tenacity import AsyncRetrying, RetryError, retry_if_exception_type, stop_after_attempt, wait_exponential

T = TypeVar("T")


async def gather_with_concurrency(limit: int, coroutines: Iterable[Awaitable[T]]) -> List[T]:
    """Run coroutines with a bounded concurrency limit."""
    semaphore = asyncio.Semaphore(limit)
    results: List[T] = []

    async def _runner(coro: Awaitable[T]) -> T:
        async with semaphore:
            return await coro

    gathered = await asyncio.gather(*(_runner(coro) for coro in coroutines), return_exceptions=True)
    for item in gathered:
        if isinstance(item, Exception):
            raise item
        results.append(item)
    return results


async def run_with_retry(
    func: Callable[..., Awaitable[T]],
    *args: Any,
    attempts: int = 3,
    wait_initial: float = 0.5,
    wait_max: float = 5.0,
    retry_exceptions: Sequence[type[BaseException]] = (Exception,),
    **kwargs: Any,
) -> T:
    """Execute an async callable with exponential backoff retries."""
    retrying = AsyncRetrying(
        stop=stop_after_attempt(attempts),
        wait=wait_exponential(multiplier=wait_initial, max=wait_max),
        retry=retry_if_exception_type(tuple(retry_exceptions)),
        reraise=True,
    )
    try:
        async for attempt in retrying:
            with attempt:
                return await func(*args, **kwargs)
    except RetryError as exc:  # pragma: no cover - tenacity wraps final failure
        raise exc.last_attempt.exception() from exc


async def to_thread(func: Callable[..., T], /, *args: Any, **kwargs: Any) -> T:
    """Run blocking function in thread using anyio."""
    return await anyio.to_thread.run_sync(func, *args, **kwargs)


async def with_timeout(coro: Awaitable[T], timeout: float) -> T:
    """Apply asyncio timeout helper."""
    return await asyncio.wait_for(coro, timeout)


__all__ = [
    "gather_with_concurrency",
    "run_with_retry",
    "to_thread",
    "with_timeout",
]
