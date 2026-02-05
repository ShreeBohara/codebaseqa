import httpx
import json
import logging
from typing import AsyncGenerator, Dict, List
from src.core.llm.base import BaseLLM

logger = logging.getLogger(__name__)

class OllamaLLM(BaseLLM):
    """Ollama LLM service for local model inference."""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.1"):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = 120
    
    async def generate(self, messages: List[Dict[str, str]], use_cache: bool = True, **kwargs) -> str:
        """Generate response using Ollama API."""
        from src.core.cache.llm_cache import get_llm_cache
        cache = get_llm_cache()

        # Check cache first
        if use_cache:
            cached = cache.get(messages, self._model)
            if cached:
                return cached

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/api/chat",
                    json={"model": self._model, "messages": messages, "stream": False}
                )
                response.raise_for_status()
                result = response.json()["message"]["content"]
                
                # Cache result
                if use_cache:
                    cache.set(messages, self._model, result)
                    
                return result
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise

    async def generate_stream(self, messages: List[Dict[str, str]]) -> AsyncGenerator[str, None]:
        """Generate streaming response using Ollama API."""
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/api/chat",
                    json={"model": self._model, "messages": messages, "stream": True}
                ) as response:
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                if "message" in data and "content" in data["message"]:
                                    yield data["message"]["content"]
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            logger.error(f"Ollama streaming failed: {e}")
            yield f"\n\n[Error: {str(e)[:100]}]"
    
    async def health_check(self) -> bool:
        """Check Ollama availability."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                # Check /api/tags to see if service is up
                response = await client.get(f"{self._base_url}/api/tags")
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False
