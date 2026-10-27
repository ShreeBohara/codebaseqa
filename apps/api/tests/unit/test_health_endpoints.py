"""Deployment readiness is local; diagnostics tolerate slow/unavailable providers."""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from src import dependencies, main
from src.core.llm.openai_llm import OpenAILLM


@pytest.mark.parametrize("ready,code,status", [(True, 200, "healthy"), (False, 503, "starting")])
async def test_readiness_never_checks_dependencies(async_client, monkeypatch, ready, code, status):
    monkeypatch.setitem(main.app.state._state, "ready", ready)
    def unexpected():
        raise AssertionError("Readiness must not inspect dependencies")
    for name in ("get_llm_service", "get_db_engine", "get_vector_store"):
        monkeypatch.setattr(dependencies, name, unexpected)
    response = await asyncio.wait_for(async_client.get("/health"), timeout=0.5)
    assert response.status_code == code
    assert response.json() == {"status": status, "version": main.app.version}


@pytest.fixture
def diagnostic_dependencies(monkeypatch):
    monkeypatch.setattr(main.settings, "demo_mode", False)
    monkeypatch.setattr(dependencies, "get_db_engine", lambda: MagicMock())
    monkeypatch.setattr(dependencies, "get_vector_store", lambda: object())
    llm = MagicMock()
    llm.health_check = AsyncMock(return_value=True)
    monkeypatch.setattr(dependencies, "get_llm_service", lambda: llm)
    async def github_response(self, url, **kwargs):
        return httpx.Response(200, json={"resources": {"core": {"remaining": 1, "limit": 60}}})
    # Patch send, not get: the test client also uses get to call the ASGI app.
    original_send = httpx.AsyncClient.send
    async def send(self, request, **kwargs):
        if request.url.host == "api.github.com":
            return await github_response(self, request.url)
        return await original_send(self, request, **kwargs)
    monkeypatch.setattr(httpx.AsyncClient, "send", send)
    return llm


async def test_diagnostics_preserves_shape(async_client, diagnostic_dependencies):
    response = await async_client.get("/health/details")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert set(body["checks"]) == {"database", "vector_store", "llm_provider", "github_api", "demo_repo"}
    assert {"version", "llm_provider", "embedding_provider"} <= body.keys()


async def test_slow_provider_is_bounded_and_does_not_break_readiness(
    async_client, diagnostic_dependencies, monkeypatch
):
    cancelled = asyncio.Event()
    async def slow():
        try:
            await asyncio.sleep(60)
        finally:
            cancelled.set()
    diagnostic_dependencies.health_check.side_effect = slow
    monkeypatch.setattr(main, "DEPENDENCY_CHECK_TIMEOUT_SECONDS", 0.02)
    monkeypatch.setitem(main.app.state._state, "ready", True)
    response = await asyncio.wait_for(async_client.get("/health/details"), timeout=1)
    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["checks"]["llm_provider"].startswith("error")
    assert cancelled.is_set()
    assert (await async_client.get("/health")).status_code == 200


async def test_missing_vector_store_is_degraded(async_client, diagnostic_dependencies, monkeypatch):
    monkeypatch.setattr(dependencies, "get_vector_store", lambda: None)
    response = await async_client.get("/health/details")
    assert response.json()["status"] == "degraded"


async def test_openai_health_disables_retries_only_for_probe(monkeypatch):
    llm = OpenAILLM(api_key="test", model="test")
    probe = MagicMock()
    probe.models.list = AsyncMock(return_value=object())
    options = MagicMock(return_value=probe)
    monkeypatch.setattr(llm._client, "with_options", options)
    original_retries = llm._client.max_retries
    assert await llm.health_check() is True
    options.assert_called_once_with(timeout=2.0, max_retries=0)
    assert llm._client.max_retries == original_retries


async def test_slow_github_is_bounded(async_client, diagnostic_dependencies, monkeypatch):
    original_send = httpx.AsyncClient.send
    cancelled = asyncio.Event()
    async def send(self, request, **kwargs):
        if request.url.host == "api.github.com":
            try:
                await asyncio.sleep(60)
            finally:
                cancelled.set()
        return await original_send(self, request, **kwargs)
    monkeypatch.setattr(httpx.AsyncClient, "send", send)
    monkeypatch.setattr(main, "DEPENDENCY_CHECK_TIMEOUT_SECONDS", 0.02)
    response = await asyncio.wait_for(async_client.get("/health/details"), timeout=1)
    assert response.json()["status"] == "degraded"
    assert response.json()["checks"]["github_api"].startswith("error")
    assert cancelled.is_set()
