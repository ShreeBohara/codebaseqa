"""
FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from src.config import settings
from src.api.routes import repos, chat, search
from src.models.database import init_db
from src.dependencies import get_db_engine, get_vector_store

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


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for container orchestration."""
    from src.dependencies import get_db_engine
    
    checks = {"database": "ok", "vector_store": "ok"}
    
    # Check database
    try:
        engine = get_db_engine()
        with engine.connect() as conn:
            conn.execute("SELECT 1")
    except Exception as e:
        checks["database"] = f"error: {str(e)[:50]}"
    
    # Check vector store
    try:
        vs = get_vector_store()
        if vs._client is None:
            checks["vector_store"] = "not initialized"
    except Exception as e:
        checks["vector_store"] = f"error: {str(e)[:50]}"
    
    all_ok = all(v == "ok" for v in checks.values())
    
    return {
        "status": "healthy" if all_ok else "degraded",
        "version": "0.1.0",
        "checks": checks
    }


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
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
