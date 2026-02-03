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
