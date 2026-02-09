"""
OpenAI embedding service.
Uses text-embedding-3-small by default.
"""

import asyncio
import logging
import random
import threading
import time
from typing import List, Sequence

import tiktoken
from openai import AsyncOpenAI, RateLimitError

from src.core.embeddings.base import BaseEmbeddings

logger = logging.getLogger(__name__)


class OpenAIEmbeddings(BaseEmbeddings):
    """OpenAI embedding service."""

    def __init__(
        self,
        api_key: str = None,
        model: str = "text-embedding-3-small",
        base_url: str | None = None,
        max_tokens_per_request: int = 250000,
        max_texts_per_request: int = 128,
        request_concurrency: int = 1,
        min_seconds_between_requests: float = 0.0,
        rate_limit_max_retries: int = 6,
        rate_limit_base_backoff_seconds: float = 1.0,
        rate_limit_max_backoff_seconds: float = 30.0,
    ):
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        self._client = AsyncOpenAI(**client_kwargs)
        self._model = model
        self._dimensions = 1536
        self._max_tokens = 8000  # Leave some buffer from 8192 limit
        self._max_tokens_per_request = max(1, max_tokens_per_request)
        self._max_texts_per_request = max(1, max_texts_per_request)
        self._request_concurrency = max(1, request_concurrency)
        self._request_semaphore = asyncio.Semaphore(self._request_concurrency)
        self._min_seconds_between_requests = max(0.0, float(min_seconds_between_requests))
        self._rate_limit_max_retries = max(0, int(rate_limit_max_retries))
        self._rate_limit_base_backoff_seconds = max(0.1, float(rate_limit_base_backoff_seconds))
        self._rate_limit_max_backoff_seconds = max(
            self._rate_limit_base_backoff_seconds,
            float(rate_limit_max_backoff_seconds),
        )
        self._request_pacing_lock = threading.Lock()
        self._next_request_time = 0.0
        try:
            self._tokenizer = tiktoken.encoding_for_model(model)
        except KeyError:
            self._tokenizer = tiktoken.get_encoding("cl100k_base")

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def _truncate_text(self, text: str) -> str:
        """Truncate text to fit within token limit."""
        tokens = self._tokenizer.encode(text)
        if len(tokens) > self._max_tokens:
            tokens = tokens[:self._max_tokens]
            return self._tokenizer.decode(tokens)
        return text

    def _create_batches(self, texts: List[str]) -> List[List[str]]:
        """Create embedding batches bounded by token budget and item count."""
        batches: List[List[str]] = []
        current_batch: List[str] = []
        current_tokens = 0

        for text in texts:
            text_tokens = len(self._tokenizer.encode(text))
            exceeds_token_budget = current_tokens + text_tokens > self._max_tokens_per_request
            exceeds_item_budget = len(current_batch) >= self._max_texts_per_request

            if current_batch and (exceeds_token_budget or exceeds_item_budget):
                batches.append(current_batch)
                current_batch = []
                current_tokens = 0

            current_batch.append(text)
            current_tokens += text_tokens

        if current_batch:
            batches.append(current_batch)

        return batches

    async def _wait_for_request_slot(self) -> None:
        """Throttle request cadence when minimum spacing is configured."""
        if self._min_seconds_between_requests <= 0:
            return

        now = time.monotonic()
        sleep_for = 0.0

        # Use a thread-safe lock because this singleton can be used across worker threads.
        with self._request_pacing_lock:
            if self._next_request_time > now:
                sleep_for = self._next_request_time - now
            scheduled_start = now + sleep_for
            self._next_request_time = scheduled_start + self._min_seconds_between_requests

        if sleep_for > 0:
            await asyncio.sleep(sleep_for)

    def _retry_after_seconds(self, error: RateLimitError) -> float | None:
        """Parse Retry-After hints from provider headers when present."""
        response = getattr(error, "response", None)
        if response is None:
            return None

        headers = getattr(response, "headers", None)
        if not headers:
            return None

        retry_after_ms = headers.get("retry-after-ms")
        if retry_after_ms is not None:
            try:
                return max(float(retry_after_ms) / 1000, 0.0)
            except (TypeError, ValueError):
                pass

        retry_after_seconds = headers.get("retry-after")
        if retry_after_seconds is not None:
            try:
                return max(float(retry_after_seconds), 0.0)
            except (TypeError, ValueError):
                return None

        return None

    def _rate_limit_backoff_seconds(self, attempt: int) -> float:
        base_delay = self._rate_limit_base_backoff_seconds * (2 ** attempt)
        jitter = random.uniform(0.0, 0.5)
        return min(self._rate_limit_max_backoff_seconds, base_delay + jitter)

    async def _embed_batch(self, batch: Sequence[str]) -> List[List[float]]:
        """Embed one batch while honoring global embedding concurrency limits."""
        max_attempts = self._rate_limit_max_retries + 1

        for attempt in range(max_attempts):
            async with self._request_semaphore:
                await self._wait_for_request_slot()
                try:
                    response = await self._client.embeddings.create(model=self._model, input=list(batch))
                    return [item.embedding for item in response.data]
                except RateLimitError as error:
                    if attempt == max_attempts - 1:
                        raise

                    retry_after = self._retry_after_seconds(error)
                    delay = retry_after if retry_after is not None else self._rate_limit_backoff_seconds(attempt)
                    delay = min(
                        self._rate_limit_max_backoff_seconds,
                        max(delay, self._min_seconds_between_requests),
                    )
                    logger.warning(
                        "Embedding request hit rate limit; retrying in %.2fs (attempt %d/%d)",
                        delay,
                        attempt + 1,
                        max_attempts,
                    )

            await asyncio.sleep(delay)

        # Defensive fallback; loop either returns or raises.
        return []

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts with token-aware batching."""
        if not texts:
            return []

        all_embeddings = []

        # Truncate texts to fit within per-text token limit
        truncated_texts = [self._truncate_text(t) for t in texts]
        batches = self._create_batches(truncated_texts)

        # Keep default path sequential to minimize provider pressure and memory usage.
        if self._request_concurrency == 1:
            for batch in batches:
                all_embeddings.extend(await self._embed_batch(batch))
            return all_embeddings

        # Process batches in parallel only when explicitly configured.
        batch_embeddings = await asyncio.gather(*[self._embed_batch(batch) for batch in batches])
        for embeddings in batch_embeddings:
            all_embeddings.extend(embeddings)

        return all_embeddings

    async def embed_query(self, query: str) -> List[float]:
        """Embed single query."""
        truncated = self._truncate_text(query)
        response = await self._client.embeddings.create(model=self._model, input=truncated)
        return response.data[0].embedding
