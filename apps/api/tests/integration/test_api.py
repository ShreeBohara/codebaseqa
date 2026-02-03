import pytest
from unittest.mock import MagicMock, patch
from src.models.schemas import RepoCreate

def test_list_repos_empty(client):
    """Test listing repositories when DB is empty."""
    with patch("src.api.routes.repos.get_db") as mock_get_db:
        mock_db = MagicMock()
        mock_db.query.return_value.all.return_value = []
        mock_db.query.return_value.count.return_value = 0
        mock_get_db.return_value = mock_db
        
        # Override dependency
        from src.dependencies import get_db
        app_client = client
        app_client.app.dependency_overrides[get_db] = lambda: mock_db
        
        response = app_client.get("/api/repos")
        assert response.status_code == 200
        assert response.json() == {"repositories": [], "total": 0}

def test_create_repo(client):
    """Test creating a new repository."""
    repo_data = {
        "github_url": "https://github.com/fastapi/fastapi"
    }
    
    with patch("src.api.routes.repos.get_db") as mock_get_db, \
         patch("src.api.routes.repos.IndexingService") as MockIndexingService:
         
        # Mock DB
        mock_db = MagicMock()
        mock_repo = MagicMock()
        mock_repo.id = "new-repo-id"
        mock_repo.github_url = repo_data["github_url"]
        mock_repo.github_owner = "fastapi"
        mock_repo.github_name = "fastapi"
        mock_repo.github_name = "fastapi"
        mock_repo.status = "pending"
        import datetime
        mock_repo.created_at = datetime.datetime.now()
        mock_repo.last_indexed_at = None
        mock_repo.languages = []
        mock_repo.total_files = 0
        mock_repo.total_chunks = 0
        mock_repo.description = "Test Repo"
        mock_repo.primary_language = "Python"
        
        # Setup DB mocks to simulate successful creation
        mock_db.query.return_value.filter.return_value.first.return_value = None  # No existing repo
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        def refresh_side_effect(x):
            setattr(x, 'id', 'new-repo-id')
            setattr(x, 'created_at', datetime.datetime.now())
            setattr(x, 'total_files', 0)
            setattr(x, 'total_chunks', 0)
            setattr(x, 'languages', [])  # Ensure this is a list
            setattr(x, 'status', "pending")
            
        mock_db.refresh.side_effect = refresh_side_effect
        
        # Mock Indexing Service
        mock_service = MockIndexingService.return_value
        mock_service.index_repository = MagicMock()
        
        # Override dependency
        from src.dependencies import get_db
        app_client = client
        app_client.app.dependency_overrides[get_db] = lambda: mock_db
        
        response = app_client.post("/api/repos", json=repo_data)
        
        # Since we mocked DB interactions but the endpoint might be doing complex async tasks
        # or checking other things, we might get errors if not fully mocked.
        # But let's assume standard FastAPI dependency injection works.
        
        # Actually simplest way to test API with logic is mocking the service call layer if possible,
        # or mocking the DB session completely.
        
        if response.status_code not in [200, 201, 202]:
            print(response.json())
        
        # 200 OK is returned by default for success in routes
        assert response.status_code == 200
        data = response.json()
        assert data["github_url"] == repo_data["github_url"]
