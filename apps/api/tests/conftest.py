import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from src.main import app
from typing import AsyncGenerator

@pytest.fixture
def client() -> TestClient:
    """Synchronous test client."""
    return TestClient(app)

@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Asynchronous test client for testing async endpoints."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

@pytest.fixture
def mock_repo_data():
    """Sample repository data for testing."""
    return {
        "url": "https://github.com/fastapi/fastapi",
        "owner": "fastapi",
        "name": "fastapi",
        "id": "test-repo-id"
    }
