from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.indexing_service import IndexingService, IndexingStatus


@pytest.fixture
def indexing_service():
    mock_db = MagicMock()
    return IndexingService(mock_db)


@pytest.mark.asyncio
async def test_index_repository_success(indexing_service, mock_repo_data):
    """Test successful repository indexing flow."""
    repo_id = "test-repo-id"

    # Mock all dependencies
    with patch("src.services.indexing_service.RepoManager") as MockRepoManager:

        # Mock DB
        mock_db = indexing_service._db
        mock_repo = MagicMock()
        mock_repo.id = repo_id
        mock_repo.status = IndexingStatus.PENDING
        mock_repo.github_url = "https://github.com/test/repo"
        mock_repo.github_owner = "test"
        mock_repo.github_name = "repo"
        mock_repo.default_branch = "main"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_repo

        mock_manager = MockRepoManager.return_value
        mock_manager.clone_repository = AsyncMock(return_value="/tmp/test-repo")
        mock_manager = MockRepoManager.return_value
        mock_manager.clone_repository = AsyncMock(return_value="/tmp/test-repo")
        mock_manager.get_current_commit = AsyncMock(return_value="sha123")

        # IMPORTANT: Inject the mock manager into the service instance
        # because the service was created before the patch
        indexing_service._repo_manager = mock_manager

        # Mock internal methods using patch.object context managers
        with patch.object(indexing_service, '_find_files', return_value=[]), \
             patch.object(indexing_service, '_embed_and_store', new_callable=AsyncMock), \
             patch.object(indexing_service, '_update_progress'):

            # Run indexing
            await indexing_service.index_repository(repo_id)

        # Verify status updates
        if mock_repo.status == IndexingStatus.FAILED:
            # mock_repo.indexing_error might be set as a property or called as attribute
            # Since it's MagicMock, we check how it was set.
            # Usually strict assignment: mock_repo.indexing_error = str(e)
            print(f"DEBUG: Indexing Error: {mock_repo.indexing_error}")

        assert mock_repo.status == IndexingStatus.COMPLETED
        mock_manager.clone_repository.assert_called_once()


@pytest.mark.asyncio
async def test_index_repository_failure(indexing_service):
    """Test proper error handling during indexing."""
    repo_id = "test-fail-id"

    # Mock DB
    mock_db = indexing_service._db
    mock_repo = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = mock_repo

    # Simulate cloning error
    with patch("src.services.indexing_service.RepoManager") as MockRepoManager:
        mock_manager = MockRepoManager.return_value
        mock_manager.clone_repository = AsyncMock(side_effect=Exception("Git clone failed"))

        # Inject mock
        indexing_service._repo_manager = mock_manager

        # Run indexing
        await indexing_service.index_repository(repo_id)

        # Verify status is set to FAILED
        assert mock_repo.status == IndexingStatus.FAILED
        assert "Git clone failed" in str(mock_repo.indexing_error)


def test_find_files_includes_new_extensions_and_rails_filenames(indexing_service, tmp_path):
    """Ensure newly supported source extensions and Rails filenames are indexed."""
    included_files = [
        "main.cs",
        "script.csx",
        "core.cc",
        "core.cxx",
        "core.hpp",
        "core.hh",
        "core.hxx",
        "core.ipp",
        "core.tpp",
        "task.rake",
        "library.gemspec",
        "template.erb",
        "Gemfile",
        "Rakefile",
        "config.ru",
    ]
    excluded_files = ["notes.txt", "archive.zip"]

    for file_name in included_files + excluded_files:
        (tmp_path / file_name).write_text("content", encoding="utf-8")

    found = indexing_service._find_files(tmp_path)
    found_names = {path.name for path in found}

    for file_name in included_files:
        assert file_name in found_names
    for file_name in excluded_files:
        assert file_name not in found_names


@pytest.mark.asyncio
async def test_parse_file_falls_back_to_raw_when_parser_fails(indexing_service, tmp_path):
    """Parser failures should not drop files; they should fallback to raw indexing."""
    repo = MagicMock()
    repo.id = "repo-1"
    source_path = tmp_path / "broken.rb"
    content = "def hello\n  puts 'hi'\nend\n"
    source_path.write_text(content, encoding="utf-8")

    parser = MagicMock()
    parser.parse.side_effect = RuntimeError("parser crashed")

    with patch("src.services.indexing_service.get_parser_for_file", return_value=parser):
        with patch.object(
            indexing_service,
            "_index_raw_file",
            new_callable=AsyncMock,
            return_value=[{"id": "raw-1", "content": "raw", "metadata": {"language": "ruby"}}],
        ) as raw_index:
            result = await indexing_service._parse_file(repo, source_path, tmp_path)

    raw_index.assert_awaited_once_with(repo, source_path, tmp_path, content)
    assert result == [{"id": "raw-1", "content": "raw", "metadata": {"language": "ruby"}}]


@pytest.mark.asyncio
async def test_index_raw_file_sets_rails_languages(indexing_service, tmp_path):
    """Raw indexing should tag Rails files with ruby/erb language metadata."""
    repo = MagicMock()
    repo.id = "repo-1"

    gemfile = tmp_path / "Gemfile"
    gemfile_content = "source 'https://rubygems.org'"
    gemfile.write_text(gemfile_content, encoding="utf-8")

    erb_file = tmp_path / "index.erb"
    erb_content = "<h1>Hello</h1>"
    erb_file.write_text(erb_content, encoding="utf-8")

    gem_chunks = await indexing_service._index_raw_file(repo, gemfile, tmp_path, gemfile_content)
    erb_chunks = await indexing_service._index_raw_file(repo, erb_file, tmp_path, erb_content)

    assert gem_chunks[0]["metadata"]["language"] == "ruby"
    assert erb_chunks[0]["metadata"]["language"] == "erb"
