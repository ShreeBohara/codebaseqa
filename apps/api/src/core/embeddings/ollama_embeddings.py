import httpx
import logging
from typing import List
from src.core.embeddings.base import BaseEmbeddings

logger = logging.getLogger(__name__)

class OllamaEmbeddings(BaseEmbeddings):
    """Ollama embedding service for local embeddings."""
    
    # Model -> dimensions mapping
    # Note: These are defaults, ideally we'd fetch this from model info if possible
    MODEL_DIMENSIONS = {
        "nomic-embed-text": 768,
        "mxbai-embed-large": 1024,
        "all-minilm": 384,
        "llama3": 4096,
        "llama3.1": 4096,
    }
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "nomic-embed-text",
        max_chars: int | None = None,
        num_ctx: int | None = None,
        fail_open: bool = True,
    ):
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._dimensions = self.MODEL_DIMENSIONS.get(model, 768)
        self._max_chars = max_chars
        self._num_ctx = num_ctx
        self._fail_open = fail_open
        # Try to infer dimensions if model name contains typical hints, or defaulting
    
    @property
    def dimensions(self) -> int:
        return self._dimensions
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts one at a time (Ollama currently doesn't support batching well in all versions)."""
        from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log
        import asyncio
        import json

        @retry(
            stop=stop_after_attempt(10),  # Increased from 5
            wait=wait_exponential(multiplier=1, min=2, max=30),  # More patient wait strategy
            retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError, httpx.TimeoutException)), # Catch more errors
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True
        )
        async def _embed_one(client, text):
            # Validate text
            if not text or not text.strip():
                # ROI: Return zero vector for empty text to match dimensions
                return [0.0] * self.dimensions

            # Truncate if configured (stability guard)
            content = text.strip()
            if self._max_chars and len(content) > self._max_chars:
                content = content[: self._max_chars]

            # Prepare request data
            # Simplified request to avoid VRAM/Context issues
            request_data = {
                "model": self._model,
                "prompt": content,
            }
            if self._num_ctx:
                request_data["options"] = {"num_ctx": self._num_ctx}

            response = await client.post(
                f"{self._base_url}/api/embeddings",
                json=request_data
            )
            
            if response.status_code == 404:
                logger.error(f"Model {self._model} not found in Ollama. Please run: ollama pull {self._model}")
                raise httpx.HTTPStatusError("Model not found", request=response.request, response=response)
            
            if response.status_code >= 500:
                logger.error(f"Ollama Server Error ({response.status_code}): {response.text}")

            response.raise_for_status()
            try:
                payload = response.json()
            except json.JSONDecodeError:
                logger.error(f"Ollama returned non-JSON response: {response.text[:200]}")
                raise

            if "embedding" not in payload:
                logger.error(f"Ollama response missing embedding key: {str(payload)[:200]}")
                raise ValueError("Ollama response missing embedding")

            return payload["embedding"]

        embeddings = []
        # Use a longer timeout for the client session overall, though per-request applies
        async with httpx.AsyncClient(timeout=120.0) as client:
            total = len(texts)
            for i, val in enumerate(texts):
                try:
                    # Add delay to prevent overwhelming Ollama (increased to 0.1s)
                    if i > 0:
                        await asyncio.sleep(0.2)  # Increased from 0.05 to 0.2
                        
                    emb = await _embed_one(client, val)
                    embeddings.append(emb)
                    
                    # Log progress periodically
                    if (i + 1) % 10 == 0:
                         logger.debug(f"Embedded {i+1}/{total} chunks")
                         
                except Exception as e:
                    logger.error(f"Ollama embedding failed at index {i} (text length: {len(val)}): {e}")
                    if self._fail_open:
                        embeddings.append([0.0] * self.dimensions)
                        continue
                    raise

        return embeddings
    
    async def embed_query(self, query: str) -> List[float]:
        """Embed single query."""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                request_data = {
                    "model": self._model,
                    "prompt": query,
                }
                if self._max_chars and len(request_data["prompt"]) > self._max_chars:
                    request_data["prompt"] = request_data["prompt"][: self._max_chars]
                if self._num_ctx:
                    request_data["options"] = {"num_ctx": self._num_ctx}

                response = await client.post(
                    f"{self._base_url}/api/embeddings",
                    json=request_data
                )
                response.raise_for_status()
                return response.json()["embedding"]
        except Exception as e:
            logger.error(f"Ollama embedding failed for query: {e}")
            raise
