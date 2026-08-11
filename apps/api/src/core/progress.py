"""
Shared indexing-progress store.

WHY THIS EXISTS
IndexingService wrote progress into a per-instance dict. The SSE endpoint constructs a
fresh IndexingService per request, so it never saw those writes and always fell through to
the database branch, which hardcodes current_step="Unknown" and a percentage of 0 or 100.
The per-file progress the indexer computes was therefore unreachable by any client, and
the progress bar could only ever show 0% or 100%.

A per-process dict cannot fix this either: indexing runs in a background task and, under
more than one worker, in a different process from the request that wants to read it.

DESIGN
A Redis stream per repository (progress:{repo_id}), capped with MAXLEN so it cannot grow
without bound. Redis is optional throughout this codebase, so there is an in-memory
fallback that is correct within a single process -- which is the local-dev shape. The
fallback is explicitly not cross-process, and callers can tell which backend is live via
`backend`.

Streams rather than a plain key because the SSE endpoint wants *history*: a client that
connects late should be able to replay what it missed rather than only seeing the current
value, and XRANGE gives that for free.
"""

from __future__ import annotations

import json
import logging
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Any, Deque, Dict, List, Optional

logger = logging.getLogger(__name__)

# Enough to replay a long index without unbounded growth. Each entry is small.
_STREAM_MAXLEN = 500
_MEMORY_MAXLEN = 500


def _stream_key(repo_id: str) -> str:
    return f"progress:{repo_id}"


class ProgressStore:
    """
    Publishes and reads indexing progress.

    Safe to construct per request; the Redis client it wraps is the shared singleton.
    """

    def __init__(self, redis_client=None):
        self._redis = redis_client
        # Class-level so every instance in a process shares the fallback, which is the
        # whole point -- a per-instance dict is the bug this replaces.
        self._lock = _MEMORY_LOCK
        self._memory = _MEMORY

    @property
    def backend(self) -> str:
        return "redis" if self._redis is not None else "memory"

    async def publish(
        self,
        repo_id: str,
        status: str,
        step: str,
        percent: float,
        files_processed: int = 0,
        total_files: int = 0,
    ) -> None:
        """Record a progress event. Never raises -- progress must not break indexing."""
        event = {
            "repo_id": repo_id,
            "status": status,
            "current_step": step,
            "progress_percent": round(float(percent), 2),
            "files_processed": int(files_processed),
            "total_files": int(total_files),
            "at": time.time(),
        }

        if self._redis is not None:
            try:
                await self._redis.xadd(
                    _stream_key(repo_id),
                    {"event": json.dumps(event)},
                    maxlen=_STREAM_MAXLEN,
                    approximate=True,
                )
                return
            except Exception as exc:
                # Fall through to memory rather than losing the event or failing the
                # index. Logged at debug because a flapping Redis would otherwise emit
                # one warning per parsed file.
                logger.debug("Progress publish to Redis failed, using memory: %s", exc)

        with self._lock:
            self._memory[repo_id].append(event)

    async def latest(self, repo_id: str) -> Optional[Dict[str, Any]]:
        """Most recent event, or None if nothing has been published."""
        if self._redis is not None:
            try:
                entries = await self._redis.xrevrange(_stream_key(repo_id), count=1)
                if entries:
                    return _decode(entries[0])
            except Exception as exc:
                logger.debug("Progress read from Redis failed, using memory: %s", exc)

        with self._lock:
            events = self._memory.get(repo_id)
            return dict(events[-1]) if events else None

    async def history(self, repo_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Oldest-first events, so a late subscriber can replay what it missed."""
        if self._redis is not None:
            try:
                entries = await self._redis.xrange(_stream_key(repo_id), count=limit)
                return [_decode(e) for e in entries]
            except Exception as exc:
                logger.debug("Progress history from Redis failed, using memory: %s", exc)

        with self._lock:
            events = self._memory.get(repo_id) or []
            return [dict(e) for e in list(events)[-limit:]]

    async def clear(self, repo_id: str) -> None:
        """Drop a repository's progress, e.g. when it is deleted or re-indexed."""
        if self._redis is not None:
            try:
                await self._redis.delete(_stream_key(repo_id))
            except Exception as exc:
                logger.debug("Progress clear in Redis failed: %s", exc)

        with self._lock:
            self._memory.pop(repo_id, None)


def _decode(entry) -> Dict[str, Any]:
    """
    Turn one stream entry into the event dict.

    Redis returns (id, {field: value}); values are bytes unless the client decodes
    responses, and this codebase does not configure that, so both are handled.
    """
    _entry_id, fields = entry
    raw = fields.get(b"event") or fields.get("event") or "{}"
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="replace")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


_MEMORY: Dict[str, Deque[Dict[str, Any]]] = defaultdict(lambda: deque(maxlen=_MEMORY_MAXLEN))
_MEMORY_LOCK = Lock()
