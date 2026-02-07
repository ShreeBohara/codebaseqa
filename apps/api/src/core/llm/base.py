from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, List


class BaseLLM(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def generate(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Generate a response (non-streaming)."""
        pass

    @abstractmethod
    async def generate_stream(
        self, messages: List[Dict[str, str]]
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the LLM provider is available."""
        pass
