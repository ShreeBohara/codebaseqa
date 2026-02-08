from src.config import settings
from src.core.embeddings.base import BaseEmbeddings
from src.core.embeddings.ollama_embeddings import OllamaEmbeddings
from src.core.embeddings.openai_embeddings import OpenAIEmbeddings


def create_embedding_service() -> BaseEmbeddings:
    """Factory function to create embedding service based on configuration."""
    provider = settings.embedding_provider.lower()

    if provider == "openai":
        return OpenAIEmbeddings(
            api_key=settings.openai_api_key,
            model=settings.openai_embedding_model,
            base_url=settings.openai_base_url,
            max_tokens_per_request=settings.openai_embedding_max_tokens_per_request,
            max_texts_per_request=settings.openai_embedding_max_texts_per_request,
            request_concurrency=settings.openai_embedding_request_concurrency,
        )
    elif provider == "ollama":
        return OllamaEmbeddings(
            base_url=settings.ollama_base_url,
            model=settings.local_embedding_model,
            max_chars=settings.ollama_embedding_max_chars,
            num_ctx=settings.ollama_embedding_num_ctx,
            fail_open=settings.ollama_embedding_fail_open,
        )
    else:
        # Fallback/Default or Raise
        # For now, if unknown, default to OpenAI if key exists, else error
        if settings.openai_api_key:
             return OpenAIEmbeddings(
                api_key=settings.openai_api_key,
                model=settings.openai_embedding_model
            )
        raise ValueError(f"Unknown embedding provider: {provider}")
