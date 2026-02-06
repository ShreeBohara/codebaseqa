from pathlib import Path

import pytest

from src.config import settings
from src.core.github.repo_manager import RepoManager


@pytest.mark.asyncio
async def test_get_file_content_reads_valid_repo_file(tmp_path, monkeypatch):
    repos_root = tmp_path / "repos"
    monkeypatch.setattr(settings, "repos_dir", str(repos_root))

    owner = "octocat"
    repo = "hello-world"
    repo_root = repos_root / owner / repo
    target = repo_root / "src" / "main.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("print('hello')", encoding="utf-8")

    manager = RepoManager()
    content = await manager.get_file_content(owner, repo, "src/main.py")

    assert content == "print('hello')"


@pytest.mark.asyncio
async def test_get_file_content_rejects_parent_traversal(tmp_path, monkeypatch):
    repos_root = tmp_path / "repos"
    monkeypatch.setattr(settings, "repos_dir", str(repos_root))

    owner = "octocat"
    repo = "hello-world"
    repo_root = repos_root / owner / repo
    repo_root.mkdir(parents=True, exist_ok=True)
    outside = repos_root / owner / "secret.txt"
    outside.write_text("do not read", encoding="utf-8")

    manager = RepoManager()
    with pytest.raises(ValueError, match="Invalid file path"):
        await manager.get_file_content(owner, repo, "../secret.txt")


@pytest.mark.asyncio
async def test_get_file_content_rejects_prefix_sibling_escape(tmp_path, monkeypatch):
    repos_root = tmp_path / "repos"
    monkeypatch.setattr(settings, "repos_dir", str(repos_root))

    owner = "octocat"
    repo = "hello-world"
    repo_root = repos_root / owner / repo
    repo_root.mkdir(parents=True, exist_ok=True)

    sibling_repo = repos_root / owner / "hello-world-evil"
    sibling_target = sibling_repo / "secret.txt"
    sibling_target.parent.mkdir(parents=True, exist_ok=True)
    sibling_target.write_text("sensitive", encoding="utf-8")

    manager = RepoManager()
    with pytest.raises(ValueError, match="Invalid file path"):
        await manager.get_file_content(owner, repo, "../hello-world-evil/secret.txt")
