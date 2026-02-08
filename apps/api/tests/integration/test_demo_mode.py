from unittest.mock import MagicMock

from src.config import settings


def test_platform_config_exposes_demo_flags(client, monkeypatch):
    mock_repo = MagicMock()
    mock_repo.id = "demo-repo-id"

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = mock_repo

    monkeypatch.setattr(settings, "demo_mode", True)
    monkeypatch.setattr(settings, "demo_repo_owner", "fastapi")
    monkeypatch.setattr(settings, "demo_repo_name", "fastapi")
    monkeypatch.setattr(settings, "demo_repo_url", "https://github.com/fastapi/fastapi")
    monkeypatch.setattr(settings, "demo_banner_text", "demo banner")
    monkeypatch.setattr(settings, "demo_allow_public_imports", False)
    monkeypatch.setattr(settings, "demo_busy_mode", False)

    from src.dependencies import get_db

    app_client = client
    app_client.app.dependency_overrides[get_db] = lambda: mock_db

    response = app_client.get("/api/platform/config")
    assert response.status_code == 200

    payload = response.json()
    assert payload["demo_mode"] is True
    assert payload["demo_repo_id"] == "demo-repo-id"
    assert payload["demo_repo_full_name"] == "fastapi/fastapi"
    assert payload["allow_public_imports"] is False

    app_client.app.dependency_overrides.clear()


def test_demo_mode_blocks_repo_import(client, monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", True)
    monkeypatch.setattr(settings, "demo_allow_public_imports", False)

    from src.dependencies import get_db

    mock_db = MagicMock()
    app_client = client
    app_client.app.dependency_overrides[get_db] = lambda: mock_db

    response = app_client.post(
        "/api/repos/",
        json={"github_url": "https://github.com/fastapi/fastapi"},
    )

    assert response.status_code == 403
    payload = response.json()
    assert payload["detail"]["code"] == "DEMO_REPO_MUTATION_DISABLED"

    app_client.app.dependency_overrides.clear()
