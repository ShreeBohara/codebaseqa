"""
Configuration management with environment variable support.
Designed for easy self-hosting with sensible defaults.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings.
    All can be overridden via environment variables.
    """

    # Application
    app_name: str = "CodebaseQA"
    debug: bool = False

    # API Server
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # Database
    database_url: str = "sqlite:///./data/codebaseqa.db"

    # Vector Store
    vector_db_type: str = "chroma"  # "chroma" or "qdrant"
    chroma_persist_dir: str = "./data/chroma"
    qdrant_url: Optional[str] = None
    qdrant_api_key: Optional[str] = None

    # LLM Providers
    llm_provider: str = "openai"  # "openai", "anthropic", "ollama"
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o"
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-sonnet-4-20250514"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    # Embedding Providers
    embedding_provider: str = "openai"  # "openai" or "ollama"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_base_url: Optional[str] = None  # Optional: OpenAI-compatible endpoint (e.g., LM Studio)
    voyage_api_key: Optional[str] = None
    voyage_model: str = "voyage-code-3"
    local_embedding_model: str = "nomic-ai/nomic-embed-text-v1.5"
    ollama_embedding_num_ctx: int = 2048  # Smaller context improves stability
    ollama_embedding_max_chars: int = 3000  # Safety cap per chunk for Ollama
    ollama_embedding_fail_open: bool = True  # Continue indexing on occasional failures

    # GitHub
    github_token: Optional[str] = None
    repos_dir: str = "./data/repos"

    # Processing limits
    max_file_size_kb: int = 500  # Skip files larger than this
    max_files_per_repo: int = 5000
    chunk_size_tokens: int = 500  # Reduced for local model stability
    chunk_overlap_tokens: int = 200

    # Supported languages
    supported_languages: List[str] = ["python", "javascript", "typescript", "java"]

    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # Graph generation (LLM prompt sizing)
    graph_max_files: int = 50
    graph_summary_max_chars: int = 200
    graph_prompt_max_chars: int = 8000
    graph_max_tokens: int = 800
    graph_llm_timeout_seconds: int = 180
    graph_min_edges: int = 8
    graph_edge_max_tokens: int = 400

    # OpenAI-compatible client defaults (LM Studio)
    openai_timeout_seconds: int = 120

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
