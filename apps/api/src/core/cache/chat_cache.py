"""Chat-specific cache with Redis + in-memory fallback."""

from __future__ import annotations

import hashlib
import json
import logging
from threading import Lock
from typing import Any, Dict, List, Optional

from cachetools import TTLCache

from src.config import settings

logger = logging.getLogger(__name__)


def _hash_payload(payload: Dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


class ChatCache:
    """Cache for embeddings, retrieval candidates, and finalized answers."""

    def __init__(self, redis_client: Any = None):
        self._redis = redis_client
        # Small in-memory fallback caches keep local/dev mode fast and resilient.
        self._embed_cache = TTLCache(maxsize=5000, ttl=max(1, settings.chat_embed_cache_ttl_seconds))
        self._retrieval_cache = TTLCache(maxsize=4000, ttl=max(1, settings.chat_retrieval_cache_ttl_seconds))
        self._answer_cache = TTLCache(maxsize=2000, ttl=max(1, settings.chat_answer_cache_ttl_seconds))
        self._lock = Lock()
        self._hits = 0
        self._misses = 0
        self._redis_errors = 0

    @property
    def redis_enabled(self) -> bool:
        return settings.chat_redis_cache_enabled and self._redis is not None

    async def _redis_get(self, key: str) -> Optional[Any]:
        if not self.redis_enabled:
            return None
        try:
            value = await self._redis.get(key)
            if value is None:
                return None
            if isinstance(value, bytes):
                value = value.decode("utf-8")
            return json.loads(value)
        except Exception as exc:
            self._redis_errors += 1
            logger.warning("Redis cache get failed for key=%s: %s", key[:24], exc)
            return None

    async def _redis_set(self, key: str, value: Any, ttl_seconds: int) -> None:
        if not self.redis_enabled:
            return
        try:
            payload = json.dumps(value, separators=(",", ":"))
            await self._redis.set(key, payload, ex=max(1, ttl_seconds))
        except Exception as exc:
            self._redis_errors += 1
            logger.warning("Redis cache set failed for key=%s: %s", key[:24], exc)

    def _local_get(self, cache: TTLCache, key: str) -> Optional[Any]:
        with self._lock:
            return cache.get(key)

    def _local_set(self, cache: TTLCache, key: str, value: Any) -> None:
        with self._lock:
            cache[key] = value

    def _key_embedding(self, query: str, model: str) -> str:
        digest = _hash_payload({"query": query.strip(), "model": model})
        return f"chat:embedding:{digest}"

    def _key_retrieval(
        self,
        repo_id: str,
        normalized_query: str,
        intent: str,
        profile: str,
        context_files: Optional[List[str]],
    ) -> str:
        digest = _hash_payload(
            {
                "repo_id": repo_id,
                "query": normalized_query,
                "intent": intent,
                "profile": profile,
                "context_files": sorted(context_files or []),
            }
        )
        return f"chat:retrieval:{digest}"

    def _key_answer(
        self,
        repo_id: str,
        question: str,
        intent: str,
        top_chunk_ids: List[str],
        model: str,
    ) -> str:
        digest = _hash_payload(
            {
                "repo_id": repo_id,
                "question": question.strip(),
                "intent": intent,
                "chunk_ids": top_chunk_ids[:12],
                "model": model,
            }
        )
        return f"chat:answer:{digest}"

    async def get_embedding(self, query: str, model: str) -> Optional[List[float]]:
        key = self._key_embedding(query, model)
        value = await self._redis_get(key)
        if value is None:
            value = self._local_get(self._embed_cache, key)
        if value is not None:
            self._hits += 1
            return value
        self._misses += 1
        return None

    async def set_embedding(self, query: str, model: str, embedding: List[float]) -> None:
        key = self._key_embedding(query, model)
        self._local_set(self._embed_cache, key, embedding)
        await self._redis_set(key, embedding, settings.chat_embed_cache_ttl_seconds)

    async def get_retrieval(
        self,
        repo_id: str,
        normalized_query: str,
        intent: str,
        profile: str,
        context_files: Optional[List[str]],
    ) -> Optional[List[Dict[str, Any]]]:
        key = self._key_retrieval(repo_id, normalized_query, intent, profile, context_files)
        value = await self._redis_get(key)
        if value is None:
            value = self._local_get(self._retrieval_cache, key)
        if value is not None:
            self._hits += 1
            return value
        self._misses += 1
        return None

    async def set_retrieval(
        self,
        repo_id: str,
        normalized_query: str,
        intent: str,
        profile: str,
        context_files: Optional[List[str]],
        candidates: List[Dict[str, Any]],
    ) -> None:
        key = self._key_retrieval(repo_id, normalized_query, intent, profile, context_files)
        self._local_set(self._retrieval_cache, key, candidates)
        await self._redis_set(key, candidates, settings.chat_retrieval_cache_ttl_seconds)

    async def get_answer(
        self,
        repo_id: str,
        question: str,
        intent: str,
        top_chunk_ids: List[str],
        model: str,
    ) -> Optional[str]:
        key = self._key_answer(repo_id, question, intent, top_chunk_ids, model)
        value = await self._redis_get(key)
        if value is None:
            value = self._local_get(self._answer_cache, key)
        if value is not None:
            self._hits += 1
            return value
        self._misses += 1
        return None

    async def set_answer(
        self,
        repo_id: str,
        question: str,
        intent: str,
        top_chunk_ids: List[str],
        model: str,
        answer: str,
    ) -> None:
        key = self._key_answer(repo_id, question, intent, top_chunk_ids, model)
        self._local_set(self._answer_cache, key, answer)
        await self._redis_set(key, answer, settings.chat_answer_cache_ttl_seconds)

    def stats(self) -> Dict[str, Any]:
        total = self._hits + self._misses
        hit_rate = (self._hits / total * 100) if total > 0 else 0.0
        return {
            "backend": "redis+memory" if self.redis_enabled else "memory",
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(hit_rate, 2),
            "embed_cache_size": len(self._embed_cache),
            "retrieval_cache_size": len(self._retrieval_cache),
            "answer_cache_size": len(self._answer_cache),
            "redis_errors": self._redis_errors,
        }
