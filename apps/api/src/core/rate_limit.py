"""Demo-mode soft throttling with Redis + in-memory fallback."""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Deque, Dict, Tuple
from uuid import uuid4

from fastapi import HTTPException, Request

from src.config import settings

logger = logging.getLogger(__name__)

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
                retry_after = max(
                    int(window_seconds - (now - events[0])) + 1,
                    settings.demo_rate_limit_cooldown_seconds,
                )
                return retry_after

            events.append(now)
            return 0

    def stats(self) -> Dict[str, int]:
        with self._lock:
            active_buckets = sum(1 for _key, values in self._events.items() if values)
        return {"active_buckets": active_buckets}


_state = _LimiterState()
_redis_client = None
_redis_errors = 0


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def _get_redis_client():
    global _redis_client
    if _redis_client is not None:
        return _redis_client

    if not settings.rate_limit_redis_enabled or not settings.redis_url:
        return None

    try:
        from src.dependencies import get_redis_client as get_shared_redis_client

        _redis_client = get_shared_redis_client()
        return _redis_client
    except Exception as exc:
        logger.warning("Rate-limit Redis unavailable; using local limiter: %s", exc)
        return None


async def _check_with_redis(key: str, limit: int, window_seconds: int) -> int:
    global _redis_errors
    redis_client = await _get_redis_client()
    if redis_client is None:
        return -1

    now_ms = int(time.time() * 1000)
    window_start = now_ms - (window_seconds * 1000)
    redis_key = f"rate:{key}"

    try:
        await redis_client.zremrangebyscore(redis_key, 0, window_start)
        count = await redis_client.zcard(redis_key)
        if count >= limit:
            oldest = await redis_client.zrange(redis_key, 0, 0, withscores=True)
            if oldest:
                oldest_ms = int(oldest[0][1])
                retry_after = max(
                    int((oldest_ms + window_seconds * 1000 - now_ms) / 1000) + 1,
                    settings.demo_rate_limit_cooldown_seconds,
                )
            else:
                retry_after = settings.demo_rate_limit_cooldown_seconds
            return retry_after

        member = f"{now_ms}-{uuid4().hex[:8]}"
        await redis_client.zadd(redis_key, {member: now_ms})
        await redis_client.expire(redis_key, max(window_seconds * 2, 60))
        return 0
    except Exception as exc:
        _redis_errors += 1
        logger.warning("Rate-limit Redis check failed for key=%s: %s", key, exc)
        return -1


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


async def enforce_demo_soft_limit(request: Request, bucket: str) -> None:
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

    retry_after = await _check_with_redis(key=key, limit=limit, window_seconds=window_seconds)
    if retry_after < 0:
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


async def get_rate_limit_stats() -> Dict[str, object]:
    redis_client = await _get_redis_client()
    return {
        "backend": "redis" if redis_client is not None else "memory",
        "redis_enabled": redis_client is not None,
        "redis_errors": _redis_errors,
        "local": _state.stats(),
    }
