"""
OpenAI embedding service.
Uses text-embedding-3-small by default.
"""

from typing import List
from openai import AsyncOpenAI
import tiktoken


class OpenAIEmbeddings:
    """OpenAI embedding service."""
    
    def __init__(self, api_key: str = None, model: str = "text-embedding-3-small"):
        self._client = AsyncOpenAI(api_key=api_key)
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
        """Embed multiple texts."""
        all_embeddings = []
        batch_size = 500  # Increased from 100 - OpenAI supports up to 2048
        
        # Truncate texts to fit within token limit
        truncated_texts = [self._truncate_text(t) for t in texts]
        
        for i in range(0, len(truncated_texts), batch_size):
            batch = truncated_texts[i:i + batch_size]
            response = await self._client.embeddings.create(model=self._model, input=batch)
            all_embeddings.extend([item.embedding for item in response.data])
        
        return all_embeddings
    
    async def embed_query(self, query: str) -> List[float]:
        """Embed single query."""
        truncated = self._truncate_text(query)
        response = await self._client.embeddings.create(model=self._model, input=truncated)
        return response.data[0].embedding

