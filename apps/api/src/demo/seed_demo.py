"""
Seed demo data for CodebaseQA.
Creates a demo repository so users can explore features immediately.

Usage:
    python -m src.demo.seed_demo

This script:
1. Adds a configured demo repository (defaults to fastapi/fastapi)
2. Triggers indexing
3. Waits for completion (optional)
"""

import asyncio
import logging
import sys
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config import settings
from src.dependencies import get_vector_store
from src.models.database import IndexingStatus, Repository, init_db
from src.services.indexing_service import IndexingService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Demo repository defaults.
# Values can be overridden via environment variables:
#   DEMO_REPO_URL, DEMO_REPO_OWNER, DEMO_REPO_NAME, DEMO_REPO_BRANCH
DEMO_REPO = {
    "github_url": settings.demo_repo_url,
    "owner": settings.demo_repo_owner,
    "name": settings.demo_repo_name,
    "branch": settings.demo_repo_branch,
    "description": f"{settings.demo_repo_owner}/{settings.demo_repo_name} - featured live demo repository",
}


def get_db_session():
    """Create database session."""
    engine = create_engine(settings.database_url)
    init_db(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def check_existing_demo(db) -> Repository | None:
    """Check if demo repo already exists."""
    return db.query(Repository).filter(
        Repository.github_owner == DEMO_REPO["owner"],
        Repository.github_name == DEMO_REPO["name"]
    ).first()


def create_demo_repo(db) -> Repository:
    """Create the demo repository record."""
    repo = Repository(
        github_url=DEMO_REPO["github_url"],
        github_owner=DEMO_REPO["owner"],
        github_name=DEMO_REPO["name"],
        default_branch=DEMO_REPO.get("branch", "main"),
        description=DEMO_REPO["description"],
        status=IndexingStatus.PENDING,
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)
    return repo


async def index_demo_repo(db, repo_id: str) -> bool:
    """Run indexing for the demo repo."""
    vector_store = get_vector_store()
    try:
        # Seed script runs outside FastAPI lifespan, so initialize store explicitly.
        await vector_store.initialize()
        service = IndexingService(db)
        await service.index_repository(repo_id)
        db.expire_all()
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        return bool(repo and repo.status == IndexingStatus.COMPLETED)
    except Exception as e:
        logger.error(f"Indexing failed: {e}", exc_info=True)
        return False
    finally:
        await vector_store.close()


def wait_for_indexing(db, repo_id: str, timeout: int = 300) -> bool:
    """Wait for indexing to complete."""
    start = time.time()
    while time.time() - start < timeout:
        db.expire_all()
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        if not repo:
            return False

        if repo.status == IndexingStatus.COMPLETED:
            return True
        elif repo.status == IndexingStatus.FAILED:
            logger.error(f"Indexing failed: {repo.indexing_error}")
            return False

        logger.info(f"Status: {repo.status}... waiting")
        time.sleep(5)

    logger.error("Indexing timed out")
    return False


async def seed_demo(wait: bool = True) -> bool:
    """
    Main function to seed demo data.

    Args:
        wait: If True, wait for indexing to complete

    Returns:
        True if successful, False otherwise
    """
    logger.info("Starting demo data seed...")

    db = get_db_session()

    try:
        # Check if already exists
        existing = check_existing_demo(db)
        if existing:
            if existing.status == IndexingStatus.COMPLETED:
                logger.info("Demo repository already indexed and ready!")
                return True
            elif existing.status == IndexingStatus.FAILED:
                logger.info("Re-indexing failed demo repository...")
                existing.status = IndexingStatus.PENDING
                existing.indexing_error = None
                db.commit()
                repo = existing
            else:
                logger.info(f"Demo repository exists with status: {existing.status}")
                if wait:
                    return wait_for_indexing(db, existing.id)
                return True
        else:
            logger.info(f"Creating demo repository: {DEMO_REPO['owner']}/{DEMO_REPO['name']}")
            repo = create_demo_repo(db)

        # Run indexing
        logger.info("Starting indexing (this may take a few minutes)...")
        success = await index_demo_repo(db, repo.id)

        if success:
            logger.info("Demo repository indexed successfully!")
            logger.info(f"  ID: {repo.id}")
            logger.info(f"  URL: {DEMO_REPO['github_url']}")
            return True
        else:
            logger.error("Demo indexing failed")
            return False

    except Exception as e:
        logger.error(f"Error seeding demo: {e}", exc_info=True)
        return False
    finally:
        db.close()


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Seed demo data for CodebaseQA")
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Don't wait for indexing to complete"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Only check if demo exists, don't create"
    )
    args = parser.parse_args()

    if args.check_only:
        db = get_db_session()
        existing = check_existing_demo(db)
        if existing and existing.status == IndexingStatus.COMPLETED:
            print(f"Demo ready: {existing.id}")
            sys.exit(0)
        else:
            print("Demo not ready")
            sys.exit(1)

    success = asyncio.run(seed_demo(wait=not args.no_wait))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
