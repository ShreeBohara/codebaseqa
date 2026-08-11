"""
Dependency injection for FastAPI.
Provides database sessions, services, and other dependencies.
"""

import logging
from functools import lru_cache
from typing import Generator

from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import settings
from src.core.cache.chat_cache import ChatCache
from src.core.llm.openai_llm import OpenAILLM
from src.core.vectorstore.chroma_store import ChromaStore
from src.services.learning_service import LearningService

logger = logging.getLogger(__name__)


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
    from src.core.embeddings.factory import create_embedding_service

    return create_embedding_service()


# LLM Service
@lru_cache()
def get_llm_service():
    """Get LLM service based on configuration."""
    from src.core.llm.factory import create_llm
    return create_llm()


def get_learning_service(
    db: Session = Depends(get_db),
    llm: OpenAILLM = Depends(get_llm_service),
    vector_store: ChromaStore = Depends(get_vector_store)
) -> LearningService:
    """Get learning service instance."""
    from src.services.learning_service import LearningService
    return LearningService(db, llm, vector_store)


def get_gamification_service(
    db: Session = Depends(get_db)
):
    """Get gamification service instance."""
    from src.services.gamification import GamificationService
    return GamificationService(db)


@lru_cache()
def get_redis_client():
    """Get Redis client when configured, otherwise return None."""
    if not settings.redis_url:
        return None

    try:
        from redis import asyncio as redis_asyncio

        return redis_asyncio.from_url(settings.redis_url)
    except Exception as exc:
        logger.warning("Redis unavailable, falling back to in-memory cache: %s", exc)
        return None


@lru_cache()
def get_chat_cache() -> ChatCache:
    """Get chat cache service with Redis+memory fallback."""
    return ChatCache(redis_client=get_redis_client())


@lru_cache()
def get_graph_driver():
    """
    Long-lived Neo4j async driver, or None when the graph read model is disabled.

    The driver owns a connection pool, so it must be a singleton and must be closed on
    shutdown (see main.py lifespan). Returns None rather than raising so that every
    caller can treat "no graph store" as an ordinary fallback path.
    """
    if not settings.neo4j_enabled:
        return None
    if not settings.neo4j_password:
        logger.warning("NEO4J_ENABLED is set but NEO4J_PASSWORD is empty; graph store disabled")
        return None

    try:
        from neo4j import AsyncGraphDatabase

        return AsyncGraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
    except Exception as exc:
        logger.warning("Neo4j driver unavailable, falling back to SQL graph: %s", exc)
        return None


def get_graph_store():
    """Neo4jGraphStore bound to the shared driver, or None when disabled."""
    driver = get_graph_driver()
    if driver is None:
        return None
    from src.core.graph.neo4j_store import Neo4jGraphStore

    return Neo4jGraphStore(driver, database=settings.neo4j_database)


def get_progress_store():
    """Shared indexing-progress store (Redis stream, memory fallback)."""
    from src.core.progress import ProgressStore

    return ProgressStore(redis_client=get_redis_client())
