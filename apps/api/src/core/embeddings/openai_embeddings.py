"""
OpenAI embedding service.
Uses text-embedding-3-small by default.
"""

import asyncio
from typing import List, Sequence

import tiktoken
from openai import AsyncOpenAI

from src.core.embeddings.base import BaseEmbeddings


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

    async def _embed_batch(self, batch: Sequence[str]) -> List[List[float]]:
        """Embed one batch while honoring global embedding concurrency limits."""
        async with self._request_semaphore:
            response = await self._client.embeddings.create(model=self._model, input=list(batch))
        return [item.embedding for item in response.data]

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
