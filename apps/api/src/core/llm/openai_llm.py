"""
OpenAI LLM service with streaming support.
"""

import asyncio
import logging
from typing import AsyncGenerator, Callable, Dict, List

from openai import (
    APIStatusError,
    AsyncOpenAI,
    AuthenticationError,
    NotFoundError,
    PermissionDeniedError,
)

from src.core.llm.base import BaseLLM, stream_error_text

logger = logging.getLogger(__name__)


class OpenAILLM(BaseLLM):
    """OpenAI LLM service with retry logic."""

    def __init__(
        self,
        api_key: str | Callable[[], str] | None = None,
        model: str = "gpt-4o",
        base_url: str | None = None,
        provider_label: str = "openai",
    ):
        # api_key accepts a callable so a token provider (e.g. Entra ID) can be passed
        # without this class needing to know how the credential is obtained.
        client_kwargs = {"api_key": api_key}
        if base_url:
            client_kwargs["base_url"] = base_url
        self._client = AsyncOpenAI(**client_kwargs)
        self._model = model
        self._max_retries = 3
        # Only used for log messages; behaviour is identical across OpenAI-compatible hosts.
        self._provider_label = provider_label

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
                if not yielded:
                    # Nothing reached the client yet. Raise so the route emits a real
                    # SSE error event with a code, instead of a "successful" stream
                    # whose entire content is an error string that then gets cached
                    # and persisted as the assistant's answer.
                    raise
                yield stream_error_text(e)
                return

    async def health_check(self) -> bool:
        """
        Check provider availability.

        Distinguishes "cannot reach the provider" from "provider does not implement
        /models". Azure serves an OpenAI-compatible surface but /models enumerates
        *deployments*, and some configurations do not expose it at all -- a 404 there
        means the endpoint answered, so credentials and networking are fine and the
        service is usable. Treating that as unhealthy would report a working Azure
        deployment as down.
        """
        try:
            await self._client.models.list()
            return True
        except NotFoundError:
            logger.info(
                "%s does not expose /models; treating as reachable (endpoint responded)",
                self._provider_label,
            )
            return True
        except (AuthenticationError, PermissionDeniedError) as e:
            logger.warning("%s health check failed: bad credentials: %s", self._provider_label, e)
            return False
        except APIStatusError as e:
            # Any other HTTP status still proves the endpoint is reachable, but an
            # unexpected status is worth surfacing rather than silently passing.
            logger.warning(
                "%s health check got unexpected status %s: %s",
                self._provider_label, e.status_code, e,
            )
            return False
        except Exception as e:
            logger.warning("%s health check failed: %s", self._provider_label, e)
            return False
