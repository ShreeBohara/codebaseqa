"""
Configuration management with environment variable support.
Designed for easy self-hosting with sensible defaults.
"""

from functools import lru_cache
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    openai_embedding_max_tokens_per_request: int = 250000
    openai_embedding_max_texts_per_request: int = 128
    openai_embedding_request_concurrency: int = 1
    openai_embedding_min_seconds_between_requests: float = 0.0
    openai_embedding_rate_limit_max_retries: int = 6
    openai_embedding_rate_limit_base_backoff_seconds: float = 1.0
    openai_embedding_rate_limit_max_backoff_seconds: float = 30.0
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
    supported_languages: List[str] = [
        "python",
        "javascript",
        "typescript",
        "java",
        "go",
        "rust",
        "csharp",
        "cpp",
        "ruby",
        "erb",
    ]

    # Rate limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60
    rate_limit_redis_enabled: bool = True

    # Redis (optional, used for distributed cache/limits)
    redis_url: Optional[str] = None

    # Chat quality/scalability controls
    chat_intent_routing_enabled: bool = True
    chat_content_rerank_enabled: bool = True
    chat_docs_first_overview_enabled: bool = True
    chat_redis_cache_enabled: bool = False
    chat_intent_llm_tiebreak_enabled: bool = True
    chat_emit_meta_event: bool = True
    chat_history_max_messages: int = 20
    chat_history_max_tokens: int = 1800
    chat_context_max_chars: int = 18000
    chat_retrieval_candidate_limit: int = 24
    chat_rerank_candidate_limit: int = 18
    chat_request_timeout_seconds: int = 90
    chat_concurrency_wait_seconds: float = 2.0
    chat_max_concurrent_per_repo: int = 4
    chat_retrieval_cache_ttl_seconds: int = 600
    chat_answer_cache_ttl_seconds: int = 1800
    chat_embed_cache_ttl_seconds: int = 3600

    # Graph generation (LLM prompt sizing)
    graph_max_files: int = 50
    graph_summary_max_chars: int = 300  # Increased for more context
    graph_prompt_max_chars: int = 10000  # Larger prompt budget
    graph_max_tokens: int = 1000  # Allow longer LLM response
    graph_llm_timeout_seconds: int = 180
    graph_min_edges: int = 15  # Require more edges before accepting
    graph_edge_max_tokens: int = 600  # More tokens for edge-only generation
    graph_include_orphans: bool = False  # Filter out disconnected nodes
    graph_v2_enabled: bool = True
    graph_v2_max_nodes: int = 160
    graph_v2_max_edges: int = 600
    graph_v2_enrich_descriptions: bool = False
    graph_v2_enrich_top_k: int = 24
    graph_dense_mode_v21: bool = True
    graph_v21_auto_nodes_threshold: int = 90
    graph_v21_auto_edges_threshold: int = 240
    graph_v21_scope_max_nodes: int = 220
    graph_v21_scope_max_edges: int = 420
    graph_v21_module_max_nodes: int = 120
    graph_v21_module_max_edges: int = 260
    graph_v21_cache_ttl_seconds: int = 45
    graph_v21_cache_max_entries: int = 64
    graph_v21_edge_budget_file_per_node: int = 10
    graph_v21_edge_budget_module_per_node: int = 14
    graph_v22_min_cross_module_ratio_for_overview: float = 0.08
    graph_v22_min_cross_module_edges_for_overview: int = 18
    graph_v22_module_filter_orphans: bool = False

    # OpenAI-compatible client defaults (LM Studio)
    openai_timeout_seconds: int = 120

    # Demo mode controls
    demo_mode: bool = False
    demo_repo_url: str = "https://github.com/fastapi/fastapi"
    demo_repo_owner: str = "fastapi"
    demo_repo_name: str = "fastapi"
    demo_repo_branch: str = "master"
    demo_allow_public_imports: bool = False
    demo_banner_text: str = (
        "Live demo mode: this deployment is pinned to one featured repository. "
        "For your own repository, self-host with your API key."
    )
    demo_busy_mode: bool = False

    # Demo soft guardrails
    demo_rate_limit_enabled: bool = True
    demo_rate_limit_cooldown_seconds: int = 30
    demo_chat_requests: int = 18
    demo_chat_window_seconds: int = 60
    demo_curriculum_requests: int = 6
    demo_curriculum_window_seconds: int = 60
    demo_lesson_requests: int = 8
    demo_lesson_window_seconds: int = 60
    demo_graph_requests: int = 5
    demo_graph_window_seconds: int = 60
    demo_challenge_requests: int = 10
    demo_challenge_window_seconds: int = 60

    # Learning V2 controls
    learning_v2_enabled: bool = False
    learning_cache_ttl_days: int = 7
    learning_prompt_version: str = "learning_v2_1"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        """
        Accept JSON lists or comma-separated strings for CORS_ORIGINS.
        """
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return []
            if stripped.startswith("["):
                return value
            return [origin.strip() for origin in stripped.split(",") if origin.strip()]
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
