"""Utilities for runtime demo-mode behavior and single-repo enforcement."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from src.config import settings
from src.models.database import Repository


def _normalize_url(url: str) -> str:
    return url.rstrip("/").lower()


def _repo_full_name(owner: str, name: str) -> str:
    return f"{owner.strip()}/{name.strip()}"


def is_demo_mode() -> bool:
    return bool(settings.demo_mode)


def is_demo_repo(repo: Repository) -> bool:
    if not repo:
        return False

    owner_match = repo.github_owner.lower() == settings.demo_repo_owner.lower()
    name_match = repo.github_name.lower() == settings.demo_repo_name.lower()
    url_match = _normalize_url(repo.github_url) == _normalize_url(settings.demo_repo_url)
    return (owner_match and name_match) or url_match


def get_demo_repository(db: Session) -> Optional[Repository]:
    repo = (
        db.query(Repository)
        .filter(
            Repository.github_owner == settings.demo_repo_owner,
            Repository.github_name == settings.demo_repo_name,
        )
        .first()
    )
    if repo:
        return repo

    return db.query(Repository).filter(Repository.github_url == settings.demo_repo_url).first()


def assert_demo_repo_access(db: Session, repo_id: str) -> None:
    """Ensure requested repository is the single allowed demo repository."""
    if not is_demo_mode():
        return

    demo_repo = get_demo_repository(db)
    if not demo_repo:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "DEMO_NOT_READY",
                "message": "Demo repository is still initializing. Please retry shortly.",
            },
        )

    if repo_id != demo_repo.id:
        raise HTTPException(
            status_code=404,
            detail={
                "code": "DEMO_REPO_ONLY",
                "message": (
                    "This live demo is limited to one featured repository. "
                    "Use self-host mode to analyze your own repositories."
                ),
            },
        )


def assert_demo_repo_mutation_allowed(action: str) -> None:
    """Gate create/delete operations in demo mode."""
    if not is_demo_mode():
        return

    if action == "import" and settings.demo_allow_public_imports:
        return

    raise HTTPException(
        status_code=403,
        detail={
            "code": "DEMO_REPO_MUTATION_DISABLED",
            "message": (
                "Repository import and deletion are disabled in live demo mode. "
                "Use the featured repository or self-host with your own API key."
            ),
        },
    )


def get_platform_config_payload(db: Session) -> dict[str, Any]:
    demo_repo = get_demo_repository(db) if is_demo_mode() else None

    return {
        "demo_mode": is_demo_mode(),
        "demo_repo_id": demo_repo.id if demo_repo else None,
        "demo_repo_full_name": _repo_full_name(settings.demo_repo_owner, settings.demo_repo_name),
        "demo_repo_url": settings.demo_repo_url,
        "demo_banner_text": settings.demo_banner_text,
        "allow_public_imports": settings.demo_allow_public_imports,
        "busy_mode": settings.demo_busy_mode,
    }
