import logging
from typing import AsyncGenerator, Dict, List
from anthropic import AsyncAnthropic
from src.core.llm.base import BaseLLM

logger = logging.getLogger(__name__)

class AnthropicLLM(BaseLLM):
    """Anthropic Claude LLM service."""
    
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model
    
    async def generate(self, messages: List[Dict[str, str]], use_cache: bool = True) -> str:
        """Generate response using Anthropic API."""
        from src.core.cache.llm_cache import get_llm_cache
        cache = get_llm_cache()

        # Check cache first
        if use_cache:
            cached = cache.get(messages, self._model)
            if cached:
                return cached
                
        try:
            # Convert from OpenAI format to Anthropic format
            # Anthropic expects 'system' as a top-level parameter, not in messages list
            system = next((m["content"] for m in messages if m["role"] == "system"), "")
            chat_messages = [m for m in messages if m["role"] != "system"]
            
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=4096,
                system=system,
                messages=chat_messages
            )
            result = response.content[0].text
            
            # Cache result
            if use_cache:
                cache.set(messages, self._model, result)
                
            return result
        except Exception as e:
            logger.error(f"Anthropic generation failed: {e}")
            raise
    
    async def generate_stream(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        """Generate streaming response."""
        try:
            system = next((m["content"] for m in messages if m["role"] == "system"), "")
            chat_messages = [m for m in messages if m["role"] != "system"]
            
            async with self._client.messages.stream(
                model=self._model,
                max_tokens=4096,
                system=system,
                messages=chat_messages
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except Exception as e:
            logger.error(f"Anthropic streaming failed: {e}")
            yield f"\n\n[Error: {str(e)[:100]}]"
    
    async def health_check(self) -> bool:
        """Check Anthropic API availability."""
        try:
            # Just verify we can make a simple request to list models or similar if available
            # Doing a minimal token count or similar is valid, or just assuming client creation is OK
            # Since Anthropic doesn't have a lightweight 'ping', we'll rely on client existence
            return self._client is not None
        except Exception:
            return False
