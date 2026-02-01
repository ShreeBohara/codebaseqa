"""
OpenAI LLM service with streaming support.
"""

from typing import List, Dict, AsyncGenerator
from openai import AsyncOpenAI
import asyncio
import logging

logger = logging.getLogger(__name__)


class OpenAILLM:
    """OpenAI LLM service with retry logic."""
    
    def __init__(self, api_key: str = None, model: str = "gpt-4o"):
        self._client = AsyncOpenAI(api_key=api_key)
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
    
    async def generate(self, messages: List[Dict[str, str]]) -> str:
        """Generate a response (non-streaming) with retry."""
        async def _call():
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                timeout=60,  # 60 second timeout
            )
            return response.choices[0].message.content
        
        return await self._retry_with_backoff(_call)
    
    async def generate_stream(
        self, 
        messages: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response."""
        try:
            stream = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                stream=True,
                timeout=120,  # 2 minute timeout for streaming
            )
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"Streaming generation failed: {e}")
            yield f"\n\n[Error: {str(e)[:100]}]"

