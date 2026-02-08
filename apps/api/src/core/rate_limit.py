"""In-memory soft throttling for public demo endpoints."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock
from typing import Deque, Dict, Tuple

from fastapi import HTTPException, Request

from src.config import settings

BucketConfig = Tuple[int, int]  # (limit, window_seconds)


def _bucket_limits() -> Dict[str, BucketConfig]:
    return {
        "chat": (settings.demo_chat_requests, settings.demo_chat_window_seconds),
        "curriculum": (settings.demo_curriculum_requests, settings.demo_curriculum_window_seconds),
        "lesson": (settings.demo_lesson_requests, settings.demo_lesson_window_seconds),
        "graph": (settings.demo_graph_requests, settings.demo_graph_window_seconds),
        "challenge": (settings.demo_challenge_requests, settings.demo_challenge_window_seconds),
    }


class _LimiterState:
    def __init__(self) -> None:
        self._events: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, limit: int, window_seconds: int) -> int:
        now = time.time()

        with self._lock:
            events = self._events[key]
            while events and now - events[0] > window_seconds:
                events.popleft()

            if len(events) >= limit:
                retry_after = max(int(window_seconds - (now - events[0])) + 1, settings.demo_rate_limit_cooldown_seconds)
                return retry_after

            events.append(now)
            return 0


_state = _LimiterState()


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _raise_busy_mode() -> None:
    raise HTTPException(
        status_code=503,
        detail={
            "code": "DEMO_BUSY_MODE",
            "message": "The live demo is temporarily busy. Please retry in a moment.",
            "retry_after_seconds": settings.demo_rate_limit_cooldown_seconds,
        },
        headers={"Retry-After": str(settings.demo_rate_limit_cooldown_seconds)},
    )


def enforce_demo_soft_limit(request: Request, bucket: str) -> None:
    """Apply soft throttling only in demo mode; no-op in normal mode."""
    if not settings.demo_mode:
        return

    if settings.demo_busy_mode:
        _raise_busy_mode()

    if not settings.demo_rate_limit_enabled:
        return

    limits = _bucket_limits()
    if bucket not in limits:
        return

    limit, window_seconds = limits[bucket]
    key = f"{bucket}:{_client_ip(request)}"
    retry_after = _state.check(key=key, limit=limit, window_seconds=window_seconds)

    if retry_after > 0:
        raise HTTPException(
            status_code=429,
            detail={
                "code": "DEMO_RATE_LIMITED",
                "message": "The live demo is receiving heavy traffic. Please retry shortly.",
                "retry_after_seconds": retry_after,
            },
            headers={"Retry-After": str(retry_after)},
        )
