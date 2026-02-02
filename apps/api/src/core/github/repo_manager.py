"""
GitHub repository manager.
Handles cloning, updating, and managing local repository copies.
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Tuple, Optional
import logging

from src.config import settings

logger = logging.getLogger(__name__)


class RepoManager:
    """Manages GitHub repository operations."""
    
    def __init__(self):
        self._repos_dir = Path(settings.repos_dir)
        self._repos_dir.mkdir(parents=True, exist_ok=True)
    
    def parse_github_url(self, url: str) -> Tuple[str, str]:
        """Parse GitHub URL to extract owner and repo name."""
        url = url.rstrip('/')
        if url.endswith('.git'):
            url = url[:-4]
        
        parts = url.split('/')
        return parts[-2], parts[-1]
    
    def get_local_path(self, owner: str, name: str) -> Path:
        """Get local path for a repository."""
        return self._repos_dir / owner / name
    
    async def clone_repository(
        self, 
        github_url: str, 
        owner: str, 
        name: str,
        branch: str = "main"
    ) -> Path:
        """Clone a repository with shallow clone for speed."""
        local_path = self.get_local_path(owner, name)
        
        # Remove existing if present
        if local_path.exists():
            shutil.rmtree(local_path)
        
        local_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Build clone command
        cmd = [
            "git", "clone",
            "--depth", "1",
            "--single-branch",
            "--branch", branch,
        ]
        
        # Add token if available
        if settings.github_token:
            # Insert token into URL for private repos
            if "github.com" in github_url:
                url_with_auth = github_url.replace(
                    "https://github.com",
                    f"https://{settings.github_token}@github.com"
                )
                cmd.append(url_with_auth)
            else:
                cmd.append(github_url)
        else:
            cmd.append(github_url)
        
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
                raise Exception(f"Git clone failed: {result.stderr}")
            
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
        repo_root = self.get_local_path(owner, name).resolve()
        target_path = (repo_root / file_path).resolve()
        
        # Security check: Ensure target is within repo root
        if not str(target_path).startswith(str(repo_root)):
            raise ValueError(f"Invalid file path: {file_path}")
            
        if not target_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        if not target_path.is_file():
             raise ValueError(f"Path is not a file: {file_path}")

        # Read file with utf-8, ignoring errors
        with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
