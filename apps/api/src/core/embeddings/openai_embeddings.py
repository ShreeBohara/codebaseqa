"""
OpenAI embedding service.
Uses text-embedding-3-small by default.
"""

from typing import List

import tiktoken
from openai import AsyncOpenAI
from src.core.embeddings.base import BaseEmbeddings


class OpenAIEmbeddings(BaseEmbeddings):
    """OpenAI embedding service."""

    def __init__(self, api_key: str = None, model: str = "text-embedding-3-small", base_url: str | None = None):
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        self._client = AsyncOpenAI(**client_kwargs)
        self._model = model
        self._dimensions = 1536
        self._max_tokens = 8000  # Leave some buffer from 8192 limit
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

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts with token-aware batching."""
        all_embeddings = []
        max_tokens_per_request = 250000  # Leave buffer from 300k limit

        # Truncate texts to fit within per-text token limit
        truncated_texts = [self._truncate_text(t) for t in texts]

        # Create token-aware batches
        batches = []
        current_batch = []
        current_tokens = 0

        for text in truncated_texts:
            text_tokens = len(self._tokenizer.encode(text))

            # If adding this text would exceed limit, start new batch
            if current_tokens + text_tokens > max_tokens_per_request and current_batch:
                batches.append(current_batch)
                current_batch = []
                current_tokens = 0

            current_batch.append(text)
            current_tokens += text_tokens

        # Don't forget the last batch
        if current_batch:
            batches.append(current_batch)

        # Process each batch
        for batch in batches:
            response = await self._client.embeddings.create(model=self._model, input=batch)
            all_embeddings.extend([item.embedding for item in response.data])

        return all_embeddings

    async def embed_query(self, query: str) -> List[float]:
        """Embed single query."""
        truncated = self._truncate_text(query)
        response = await self._client.embeddings.create(model=self._model, input=truncated)
        return response.data[0].embedding
