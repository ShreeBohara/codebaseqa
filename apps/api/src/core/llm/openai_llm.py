"""
OpenAI LLM service with streaming support.
"""

import asyncio
import logging
from typing import AsyncGenerator, Dict, List

from openai import AsyncOpenAI

from src.core.llm.base import BaseLLM

logger = logging.getLogger(__name__)


class OpenAILLM(BaseLLM):
    """OpenAI LLM service with retry logic."""

    def __init__(self, api_key: str = None, model: str = "gpt-4o", base_url: str | None = None):
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        self._client = AsyncOpenAI(**client_kwargs)
        self._model = model
        self._max_retries = 3

    async def _retry_with_backoff(self, func, *args, **kwargs):
        """Retry with exponential backoff."""
        for attempt in range(self._max_retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if attempt == self._max_retries - 1:
                    raise
                wait_time = (2 ** attempt) + 0.5  # 1.5s, 2.5s, 4.5s
                logger.warning(f"LLM call failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                await asyncio.sleep(wait_time)

    async def generate(
        self,
        messages: List[Dict[str, str]],
        use_cache: bool = True,
        max_tokens: int | None = None,
        timeout: float | None = None,
        temperature: float | None = None,
    ) -> str:
        """Generate a response (non-streaming) with retry."""
        from src.config import settings
        from src.core.cache.llm_cache import get_llm_cache
        cache = get_llm_cache()

        # Check cache first
        if use_cache:
            cached = cache.get(messages, self._model)
            if cached:
                return cached

        async def _call():
            call_kwargs = {
                "model": self._model,
                "messages": messages,
                "timeout": timeout or settings.openai_timeout_seconds,
            }
            if max_tokens:
                call_kwargs["max_tokens"] = max_tokens
            if temperature is not None:
                call_kwargs["temperature"] = temperature
            response = await self._client.chat.completions.create(
                **call_kwargs
            )
            return response.choices[0].message.content

        result = await self._retry_with_backoff(_call)

        # Cache the result
        if use_cache:
            cache.set(messages, self._model, result)

        return result

    async def generate_stream(
        self,
        messages: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response with retry-before-first-token behavior."""
        for attempt in range(self._max_retries):
            yielded = False
            try:
                stream = await self._client.chat.completions.create(
                    model=self._model,
                    messages=messages,
                    stream=True,
                    timeout=120,  # 2 minute timeout for streaming
                )

                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yielded = True
                        yield chunk.choices[0].delta.content
                return
            except Exception as e:
                should_retry = attempt < self._max_retries - 1 and not yielded
                if should_retry:
                    wait_time = (2 ** attempt) + 0.5
                    logger.warning(
                        "Streaming call failed before first token (attempt %d/%d), retrying in %.1fs: %s",
                        attempt + 1,
                        self._max_retries,
                        wait_time,
                        e,
                    )
                    await asyncio.sleep(wait_time)
                    continue
                logger.error(f"Streaming generation failed: {e}")
                yield f"\n\n[Error: {str(e)[:100]}]"
                return

    async def health_check(self) -> bool:
        """Check OpenAI API availability."""
        try:
            # Simple models list call to verify API key
            await self._client.models.list()
            return True
        except Exception as e:
            logger.warning(f"OpenAI health check failed: {e}")
            return False
