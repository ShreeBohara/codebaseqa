"""
GitHub repository manager.
Handles cloning, updating, and managing local repository copies.
"""

import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import unquote, urlparse, urlunparse

from src.config import settings

logger = logging.getLogger(__name__)

# Hosts that may receive the GitHub token. Must be matched exactly against the
# parsed hostname -- a substring test such as `"github.com" in url` also matches
# lookalike hosts like `github.com.attacker.tld`, which would hand the token to them.
GITHUB_TOKEN_HOSTS = frozenset({"github.com", "www.github.com"})


class RepoManager:
    """Manages GitHub repository operations."""

    def __init__(self):
        self._repos_dir = Path(settings.repos_dir)
        self._repos_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _authenticated_url(github_url: str) -> str:
        """
        Return the clone URL with the GitHub token injected, but only when the URL's
        host is exactly a GitHub host. Any other host gets the URL unchanged.
        """
        token = settings.github_token
        if not token:
            return github_url

        parsed = urlparse(github_url)
        hostname = (parsed.hostname or "").lower()
        if parsed.scheme not in {"http", "https"} or hostname not in GITHUB_TOKEN_HOSTS:
            return github_url

        netloc = f"{token}@{hostname}"
        if parsed.port:
            netloc = f"{netloc}:{parsed.port}"
        return urlunparse(parsed._replace(netloc=netloc))

    @staticmethod
    def _redact(text: str) -> str:
        """
        Strip the GitHub token from subprocess output before it is logged, stored in
        Repository.indexing_error, or streamed to a client. git echoes the full clone
        URL -- credentials included -- in messages like 'fatal: repository ... not found'.
        """
        token = settings.github_token
        if not token or not text:
            return text
        return text.replace(token, "***")

    @staticmethod
    def _sanitize_repo_segment(value: str, label: str) -> str:
        segment = (value or "").strip()
        if not segment or segment in {".", ".."}:
            raise ValueError(f"Invalid repository {label}")
        if "/" in segment or "\\" in segment:
            raise ValueError(f"Invalid repository {label}")
        if not re.fullmatch(r"[A-Za-z0-9._-]+", segment):
            raise ValueError(f"Invalid repository {label}")
        return segment

    def parse_github_url(self, url: str) -> Tuple[str, str]:
        """Parse GitHub URL to extract owner and repo name."""
        parsed = urlparse(url.rstrip("/"))
        parts = [unquote(part).strip() for part in parsed.path.split("/") if part.strip()]
        if len(parts) < 2:
            raise ValueError("Invalid repository URL. Expected format: https://github.com/<owner>/<repo>")

        owner = self._sanitize_repo_segment(parts[0], "owner")
        repo = parts[1]
        if repo.endswith(".git"):
            repo = repo[:-4]
        name = self._sanitize_repo_segment(repo, "name")

        return owner, name

    def get_local_path(self, owner: str, name: str) -> Path:
        """Get local path for a repository."""
        return self._repos_dir / owner / name

    async def get_default_branch(self, github_url: str) -> str:
        """Get the default branch of a repository using git ls-remote."""
        url = self._authenticated_url(github_url)

        try:
            result = subprocess.run(
                ["git", "ls-remote", "--symref", url, "HEAD"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                # Parse output like: ref: refs/heads/master  HEAD
                for line in result.stdout.splitlines():
                    if line.startswith("ref:") and "HEAD" in line:
                        # Extract branch name from refs/heads/branch_name
                        ref_part = line.split()[1]
                        if ref_part.startswith("refs/heads/"):
                            return ref_part.replace("refs/heads/", "")
        except Exception as e:
            logger.warning(f"Failed to detect default branch: {e}")

        # Fallback to main
        return "main"

    async def clone_repository(
        self,
        github_url: str,
        owner: str,
        name: str,
        branch: str = None
    ) -> Path:
        """Clone a repository with shallow clone for speed."""
        local_path = self.get_local_path(owner, name)

        # Remove existing if present
        if local_path.exists():
            shutil.rmtree(local_path)

        local_path.parent.mkdir(parents=True, exist_ok=True)

        # Auto-detect default branch if not specified
        if not branch:
            branch = await self.get_default_branch(github_url)
            logger.info(f"Detected default branch: {branch}")

        # Build clone command
        cmd = [
            "git", "clone",
            "--depth", "1",
            "--single-branch",
            "--branch", branch,
        ]

        # Inject the token only for genuine GitHub hosts (see _authenticated_url).
        cmd.append(self._authenticated_url(github_url))

        cmd.append(str(local_path))

        logger.info(f"Cloning {github_url} to {local_path}")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minutes timeout
            )

            if result.returncode != 0:
                # Redact: stderr contains the credentialed clone URL, and this message
                # is persisted to Repository.indexing_error and served over the API.
                raise Exception(f"Git clone failed: {self._redact(result.stderr)}")

            return local_path

        except subprocess.TimeoutExpired:
            raise Exception("Clone timed out after 5 minutes")

    async def get_current_commit(self, local_path: Path) -> Optional[str]:
        """Get current commit SHA."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                cwd=str(local_path),
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception as e:
            logger.error(f"Failed to get commit: {e}")
        return None

    async def cleanup_local_repo(self, local_path: str):
        """Remove local repository copy."""
        if local_path and os.path.exists(local_path):
            shutil.rmtree(local_path)
            logger.info(f"Cleaned up {local_path}")

    async def get_file_content(self, owner: str, name: str, file_path: str) -> str:
        """Read content of a specific file in the repository."""
        requested_path = Path(file_path)
        if requested_path.is_absolute():
            raise ValueError(f"Invalid file path: {file_path}")

        repo_root = self.get_local_path(owner, name).resolve()
        target_path = (repo_root / requested_path).resolve()

        # Security check: Ensure target is within repo root
        try:
            target_path.relative_to(repo_root)
        except ValueError:
            raise ValueError(f"Invalid file path: {file_path}")

        if not target_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not target_path.is_file():
            raise ValueError(f"Path is not a file: {file_path}")

        # Read file with utf-8, ignoring errors
        with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
