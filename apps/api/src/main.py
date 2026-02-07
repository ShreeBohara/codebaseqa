"""
FastAPI application entry point.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from src.api.routes import chat, learning, repos, search
from src.config import settings
from src.dependencies import get_db_engine, get_vector_store
from src.models.database import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Initialize resources on startup, cleanup on shutdown.
    """
    from pathlib import Path

    # Startup
    logger.info("Starting CodebaseQA API...")

    # Ensure data directories exist
    Path("./data").mkdir(parents=True, exist_ok=True)
    Path(settings.chroma_persist_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.repos_dir).mkdir(parents=True, exist_ok=True)
    logger.info("Data directories initialized")

    # Initialize database
    engine = get_db_engine()
    init_db(engine)
    logger.info("Database initialized")

    # Initialize vector store
    vector_store = get_vector_store()
    await vector_store.initialize()
    logger.info("Vector store initialized")

    yield

    # Shutdown
    logger.info("Shutting down CodebaseQA API...")
    await vector_store.close()


# Create FastAPI app
app = FastAPI(
    title="CodebaseQA API",
    description="AI-powered codebase understanding and Q&A",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(repos.router, prefix="/api/repos", tags=["repositories"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
app.include_router(search.router, prefix="/api/search", tags=["search"])
app.include_router(learning.router, prefix="/api/learning", tags=["learning"])


# Health check endpoint
@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint."""
    import httpx

    from src.config import settings
    from src.dependencies import get_db_engine, get_llm_service, get_vector_store

    checks = {
        "database": "ok",
        "vector_store": "ok",
        "llm_provider": "ok",
        "github_api": "ok"
    }

    # Check database
    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as e:
        checks["database"] = f"error: {str(e)[:50]}"

    # Check vector store
    try:
        vs = get_vector_store()
        # Just check if initialized since connection might be lazy
        if not vs:
             checks["vector_store"] = "not initialized"
    except Exception as e:
        checks["vector_store"] = f"error: {str(e)[:50]}"

    # Check LLM provider
    try:
        llm = get_llm_service()
        if hasattr(llm, 'health_check'):
            is_healthy = await llm.health_check()
            checks["llm_provider"] = "ok" if is_healthy else "unavailable/unreachable"
    except Exception as e:
        checks["llm_provider"] = f"error: {str(e)[:50]}"

    # Check GitHub API rate limit
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            headers = {}
            if settings.github_token:
                headers["Authorization"] = f"token {settings.github_token}"
            response = await client.get(
                "https://api.github.com/rate_limit",
                headers=headers
            )
            if response.status_code == 200:
                data = response.json()
                remaining = data["resources"]["core"]["remaining"]
                limit = data["resources"]["core"]["limit"]
                checks["github_api"] = f"ok ({remaining}/{limit} remaining)"
            else:
                checks["github_api"] = f"error: status {response.status_code}"
    except Exception as e:
        checks["github_api"] = f"error: {str(e)[:50]}"

    all_ok = all("ok" in str(v) for v in checks.values())

    return {
        "status": "healthy" if all_ok else "degraded",
        "version": "0.2.0",
        "llm_provider": settings.llm_provider,
        "embedding_provider": settings.embedding_provider,
        "checks": checks
    }


@app.get("/openapi.json")
async def get_openapi_schema():
    """Download OpenAPI schema as JSON file."""
    return app.openapi()


@app.get("/openapi.yaml")
async def get_openapi_yaml():
    """Download OpenAPI schema as YAML."""
    import yaml
    from fastapi.responses import Response
    schema = app.openapi()
    yaml_content = yaml.dump(schema, default_flow_style=False)
    return Response(content=yaml_content, media_type="text/yaml")


@app.get("/api/cache/stats")
async def get_cache_stats():
    """Get LLM cache statistics."""
    from src.core.cache.llm_cache import get_llm_cache
    cache = get_llm_cache()
    return cache.stats()


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn

    # Setup logging before run
    from src.core.logging import setup_logging
    setup_logging()

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
