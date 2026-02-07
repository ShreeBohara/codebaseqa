from abc import ABC, abstractmethod
from typing import List


class BaseEmbeddings(ABC):
    """Abstract base class for embedding providers."""

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """Return embedding dimensions."""
        pass

    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts."""
        pass

    @abstractmethod
    async def embed_query(self, query: str) -> List[float]:
        """Embed single query."""
        pass
