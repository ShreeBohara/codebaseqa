from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, List

# Marker a provider emits inline when a stream fails *after* it has already sent
# tokens (a total failure raises instead). Callers must not cache or persist a
# response containing this -- otherwise one transient upstream error is served to
# every subsequent asker for the life of the cache entry.
STREAM_ERROR_MARKER = "[stream-error]"


def stream_error_text(exc: Exception) -> str:
    """Inline text appended to a partially-delivered stream that then failed."""
    return f"\n\n{STREAM_ERROR_MARKER} generation was interrupted: {str(exc)[:100]}"


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
