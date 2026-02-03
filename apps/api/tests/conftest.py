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

@pytest.fixture
def sample_python_code():
    return """
import os
import sys

def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

class Calculator:
    def add(self, a, b):
        return a + b
"""

@pytest.fixture
def sample_javascript_code():
    return """
function formatName(firstName, lastName) {
    return firstName + " " + lastName;
}

class User {
    constructor(name) {
        this.name = name;
    }
}
"""
