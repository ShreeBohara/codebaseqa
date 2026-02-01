"""
Repository management endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import asyncio
import json
import logging

from src.dependencies import get_db, get_vector_store, get_session_factory
from src.models.schemas import RepoCreate, RepoResponse, RepoListResponse
from src.models.database import Repository, IndexingStatus
from src.services.indexing_service import IndexingService
from src.core.github.repo_manager import RepoManager

router = APIRouter()
logger = logging.getLogger(__name__)


def run_indexing_task(repo_id: str):
    """Run async indexing in a new event loop with fresh DB session."""
    async def _run():
        # Create fresh session for background task
        SessionLocal = get_session_factory()
        db = SessionLocal()
        try:
            service = IndexingService(db)
            await service.index_repository(repo_id)
        except Exception as e:
            logger.error(f"Background indexing failed: {e}", exc_info=True)
        finally:
            db.close()
    
    # Run in new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run())
    finally:
        loop.close()


@router.post("/", response_model=RepoResponse)
async def create_repository(
    repo: RepoCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Add a new repository for indexing.
    Returns immediately, indexing happens in background.
    """
    # Parse GitHub URL
    repo_manager = RepoManager()
    owner, name = repo_manager.parse_github_url(str(repo.github_url))
    
    # Check if already exists
    existing = db.query(Repository).filter(
        Repository.github_owner == owner,
        Repository.github_name == name
    ).first()
    
    if existing:
        if existing.status == IndexingStatus.FAILED:
            # Allow re-indexing failed repos
            existing.status = IndexingStatus.PENDING
            existing.indexing_error = None
            db.commit()
            # Use proper sync wrapper for async task
            background_tasks.add_task(run_indexing_task, existing.id)
            return existing
        raise HTTPException(
            status_code=409,
            detail=f"Repository already exists with status: {existing.status}"
        )
    
    # Create new repository record
    db_repo = Repository(
        github_url=str(repo.github_url),
        github_owner=owner,
        github_name=name,
        default_branch=repo.branch or "main",
        status=IndexingStatus.PENDING,
    )
    db.add(db_repo)
    db.commit()
    db.refresh(db_repo)
    
    # Start indexing in background with sync wrapper
    background_tasks.add_task(run_indexing_task, db_repo.id)
    
    return db_repo


@router.get("/", response_model=RepoListResponse)
async def list_repositories(
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    """List all indexed repositories."""
    query = db.query(Repository)
    total = query.count()
    repos = query.offset(skip).limit(limit).all()
    
    return RepoListResponse(repositories=repos, total=total)


@router.get("/{repo_id}", response_model=RepoResponse)
async def get_repository(
    repo_id: str,
    db: Session = Depends(get_db),
):
    """Get repository details."""
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    return repo


@router.get("/{repo_id}/progress")
async def get_indexing_progress(
    repo_id: str,
    db: Session = Depends(get_db),
):
    """Stream indexing progress updates via SSE."""
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    async def progress_stream():
        """Generate SSE events for progress updates."""
        indexing_service = IndexingService(db)
        
        while True:
            progress = await indexing_service.get_progress(repo_id)
            yield f"data: {json.dumps(progress)}\n\n"
            
            if progress["status"] in ["completed", "failed"]:
                break
            
            await asyncio.sleep(1)
    
    return StreamingResponse(
        progress_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.delete("/{repo_id}")
async def delete_repository(
    repo_id: str,
    db: Session = Depends(get_db),
    vector_store = Depends(get_vector_store),
):
    """Delete a repository and all associated data."""
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    
    # Delete from vector store
    await vector_store.delete_collection(repo_id)
    
    # Delete from database
    db.delete(repo)
    db.commit()
    
    # Clean up local files
    repo_manager = RepoManager()
    await repo_manager.cleanup_local_repo(repo.local_path)
    
    return {"status": "deleted", "repo_id": repo_id}
