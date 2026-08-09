from src.config import settings
from src.core.llm.anthropic_llm import AnthropicLLM
from src.core.llm.base import BaseLLM
from src.core.llm.ollama_llm import OllamaLLM
from src.core.llm.openai_llm import OpenAILLM


def create_llm() -> BaseLLM:
    """Factory function to create LLM based on configuration."""
    provider = settings.llm_provider.lower()

    if provider == "openai":
        return OpenAILLM(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            base_url=settings.openai_base_url,
        )
    elif provider in ("azure_openai", "azure"):
        # Azure's v1 surface is OpenAI-compatible, so the same client is reused with a
        # different base_url. The deployment name takes the place of the model name.
        if not settings.azure_openai_api_key:
            raise ValueError("AZURE_OPENAI_API_KEY required for the azure_openai provider")
        if not settings.azure_openai_deployment:
            raise ValueError(
                "AZURE_OPENAI_DEPLOYMENT required for the azure_openai provider "
                "(the chat deployment name, which Azure uses in place of a model id)"
            )
        return OpenAILLM(
            api_key=settings.azure_openai_api_key,
            model=settings.azure_openai_deployment,
            base_url=settings.azure_openai_base_url(),
            provider_label="azure_openai",
        )
    elif provider == "anthropic":
        if not settings.anthropic_api_key:
            # Don't raise immediately, allow app to start but fail on use if key missing
            # or just log warning? Raising here prevents app startup if config is bad.
            # Usually better to fail fast.
            raise ValueError("ANTHROPIC_API_KEY required for Anthropic provider")
        return AnthropicLLM(
            api_key=settings.anthropic_api_key,
            model=settings.anthropic_model
        )
    elif provider == "ollama":
        return OllamaLLM(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")
