"""
Dependency injection for FastAPI.
Provides database sessions, services, and other dependencies.
"""

from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from functools import lru_cache

from src.config import settings


# Database
@lru_cache()
def get_db_engine():
    """Create database engine (cached)."""
    connect_args = {}
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    
    return create_engine(
        settings.database_url,
        connect_args=connect_args,
        pool_pre_ping=True,
    )


def get_session_factory():
    """Get session factory."""
    engine = get_db_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for database sessions.
    Usage: db: Session = Depends(get_db)
    """
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Vector Store
@lru_cache()
def get_vector_store():
    """Get vector store instance (cached)."""
    from src.core.vectorstore.chroma_store import ChromaStore
    
    embedding_service = get_embedding_service()
    
    return ChromaStore(
        persist_directory=settings.chroma_persist_dir,
        embedding_service=embedding_service,
    )


# Embedding Service
@lru_cache()
def get_embedding_service():
    """Get embedding service based on configuration."""
    from src.core.embeddings.openai_embeddings import OpenAIEmbeddings
    
    return OpenAIEmbeddings(
        api_key=settings.openai_api_key,
        model=settings.openai_embedding_model,
    )


# LLM Service
@lru_cache()
def get_llm_service():
    """Get LLM service based on configuration."""
    from src.core.llm.openai_llm import OpenAILLM
    
    return OpenAILLM(
        api_key=settings.openai_api_key,
        model=settings.openai_model,
    )
