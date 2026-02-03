"""
Repository management endpoints.
"""

import asyncio
import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.core.github.repo_manager import RepoManager
from src.dependencies import get_db, get_session_factory, get_vector_store
from src.models.database import IndexingStatus, Repository
from src.models.schemas import RepoCreate, RepoListResponse, RepoResponse
from src.services.indexing_service import IndexingService

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


@router.get("/{repo_id}/files/content")
async def get_repo_file_content(
    repo_id: str,
    path: str,
    db: Session = Depends(get_db),
):
    """Get content of a specific file."""
    repo = db.query(Repository).filter(Repository.id == repo_id).first()

    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    repo_manager = RepoManager()
    try:
        content = await repo_manager.get_file_content(repo.github_owner, repo.github_name, path)
        return {"content": content}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to read file: {e}")
        raise HTTPException(status_code=500, detail="Failed to read file content")


@router.post("/demo/seed")
async def seed_demo_repository(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Seed a demo repository for immediate exploration.
    Returns the demo repo if it exists, or creates and indexes it.
    """
    from src.demo.seed_demo import DEMO_REPO

    # Check if already exists
    existing = db.query(Repository).filter(
        Repository.github_owner == DEMO_REPO["owner"],
        Repository.github_name == DEMO_REPO["name"]
    ).first()

    if existing:
        if existing.status == IndexingStatus.COMPLETED:
            return {"status": "ready", "repo_id": existing.id, "message": "Demo repository ready"}
        elif existing.status == IndexingStatus.FAILED:
            # Re-trigger indexing
            existing.status = IndexingStatus.PENDING
            existing.indexing_error = None
            db.commit()
            background_tasks.add_task(run_indexing_task, existing.id)
            return {"status": "indexing", "repo_id": existing.id, "message": "Re-indexing demo repository"}
        else:
            return {"status": existing.status, "repo_id": existing.id, "message": f"Demo repository {existing.status}"}

    # Create new demo repo
    repo = Repository(
        github_url=DEMO_REPO["github_url"],
        github_owner=DEMO_REPO["owner"],
        github_name=DEMO_REPO["name"],
        description=DEMO_REPO["description"],
        status=IndexingStatus.PENDING,
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)

    # Start indexing in background
    background_tasks.add_task(run_indexing_task, repo.id)

    return {"status": "indexing", "repo_id": repo.id, "message": "Demo repository created and indexing started"}
