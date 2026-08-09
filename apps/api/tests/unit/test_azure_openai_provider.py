"""
Azure OpenAI provider wiring.

These tests never reach the network: they assert on how the clients are constructed,
which is where every Azure-vs-OpenAI divergence actually lives.
"""

import pytest
import tiktoken
from openai import APIStatusError, AuthenticationError, NotFoundError

from src.config import Settings
from src.core.embeddings.factory import create_embedding_service
from src.core.embeddings.openai_embeddings import OpenAIEmbeddings
from src.core.llm.factory import create_llm
from src.core.llm.openai_llm import OpenAILLM


def _azure_settings(**overrides):
    base = dict(
        llm_provider="azure_openai",
        embedding_provider="azure_openai",
        azure_openai_endpoint="https://my-resource.openai.azure.com",
        azure_openai_api_key="azure-test-key",
        azure_openai_deployment="gpt-4o-prod",
        azure_openai_embedding_deployment="embed-3-small-prod",
    )
    base.update(overrides)
    return Settings(_env_file=None, **base)


# --- base URL construction -------------------------------------------------------

@pytest.mark.parametrize(
    "endpoint,expected",
    [
        ("https://r.openai.azure.com", "https://r.openai.azure.com/openai/v1"),
        ("https://r.openai.azure.com/", "https://r.openai.azure.com/openai/v1"),
        ("https://r.openai.azure.com/openai", "https://r.openai.azure.com/openai/v1"),
        # idempotent: already-complete URLs are not double-suffixed
        ("https://r.openai.azure.com/openai/v1", "https://r.openai.azure.com/openai/v1"),
        ("https://r.openai.azure.com/openai/v1/", "https://r.openai.azure.com/openai/v1"),
    ],
)
def test_azure_base_url_normalises_endpoint(endpoint, expected):
    s = _azure_settings(azure_openai_endpoint=endpoint)
    assert s.azure_openai_base_url() == expected


def test_azure_base_url_requires_endpoint():
    s = _azure_settings(azure_openai_endpoint=None)
    with pytest.raises(ValueError, match="AZURE_OPENAI_ENDPOINT"):
        s.azure_openai_base_url()


# --- factory wiring --------------------------------------------------------------

def test_llm_factory_builds_azure_client(monkeypatch):
    settings = _azure_settings()
    monkeypatch.setattr("src.core.llm.factory.settings", settings)

    llm = create_llm()

    assert isinstance(llm, OpenAILLM)
    # The deployment name must be sent where a model id normally goes.
    assert llm._model == "gpt-4o-prod"
    assert str(llm._client.base_url).rstrip("/").endswith("/openai/v1")


def test_embedding_factory_builds_azure_client(monkeypatch):
    settings = _azure_settings()
    monkeypatch.setattr("src.core.embeddings.factory.settings", settings)

    emb = create_embedding_service()

    assert isinstance(emb, OpenAIEmbeddings)
    assert emb._model == "embed-3-small-prod"
    assert str(emb._client.base_url).rstrip("/").endswith("/openai/v1")


@pytest.mark.parametrize(
    "missing,expected",
    [
        ("azure_openai_api_key", "AZURE_OPENAI_API_KEY"),
        ("azure_openai_deployment", "AZURE_OPENAI_DEPLOYMENT"),
    ],
)
def test_llm_factory_requires_azure_config(monkeypatch, missing, expected):
    monkeypatch.setattr("src.core.llm.factory.settings", _azure_settings(**{missing: None}))
    with pytest.raises(ValueError, match=expected):
        create_llm()


def test_embedding_factory_requires_deployment(monkeypatch):
    monkeypatch.setattr(
        "src.core.embeddings.factory.settings",
        _azure_settings(azure_openai_embedding_deployment=None),
    )
    with pytest.raises(ValueError, match="AZURE_OPENAI_EMBEDDING_DEPLOYMENT"):
        create_embedding_service()


def test_unknown_embedding_provider_raises_instead_of_falling_back(monkeypatch):
    """A typo used to silently produce an OpenAI client with no tuning applied."""
    monkeypatch.setattr(
        "src.core.embeddings.factory.settings",
        _azure_settings(embedding_provider="opanai", openai_api_key="sk-present"),
    )
    with pytest.raises(ValueError, match="Unknown embedding provider"):
        create_embedding_service()


# --- tokenizer resolution --------------------------------------------------------

def test_deployment_name_does_not_silently_misresolve_tokenizer():
    """A deployment name cannot resolve in tiktoken; tokenizer_model must win."""
    with pytest.raises(KeyError):
        tiktoken.encoding_for_model("embed-3-small-prod")

    emb = OpenAIEmbeddings(
        api_key="k",
        model="embed-3-small-prod",
        tokenizer_model="text-embedding-3-small",
    )
    assert emb._tokenizer.name == tiktoken.encoding_for_model("text-embedding-3-small").name


def test_unresolvable_tokenizer_warns_rather_than_silently_falling_back(caplog):
    with caplog.at_level("WARNING"):
        emb = OpenAIEmbeddings(api_key="k", model="some-unknown-deployment")
    assert emb._tokenizer.name == "cl100k_base"
    assert "falling back to cl100k_base" in caplog.text


# --- dimensions ------------------------------------------------------------------

def test_dimensions_are_configurable():
    """text-embedding-3-large is 3072; a hardcoded 1536 breaks the Chroma insert."""
    assert OpenAIEmbeddings(api_key="k").dimensions == 1536
    assert OpenAIEmbeddings(api_key="k", dimensions=3072).dimensions == 3072


def test_embedding_factory_passes_configured_dimensions(monkeypatch):
    monkeypatch.setattr(
        "src.core.embeddings.factory.settings",
        _azure_settings(openai_embedding_dimensions=3072),
    )
    assert create_embedding_service().dimensions == 3072


# --- provider-aware health check -------------------------------------------------

def _response(status):
    import httpx
    request = httpx.Request("GET", "https://example.invalid/openai/v1/models")
    return httpx.Response(status, request=request)


@pytest.mark.asyncio
async def test_health_check_treats_missing_models_endpoint_as_reachable(monkeypatch):
    """
    Azure's /models lists deployments and some configurations omit it. A 404 means
    the endpoint answered, so the provider is usable -- reporting unhealthy here
    would mark a working deployment as down.
    """
    llm = OpenAILLM(api_key="k", model="d", provider_label="azure_openai")

    async def raise_404():
        raise NotFoundError("no models route", response=_response(404), body=None)

    monkeypatch.setattr(llm._client.models, "list", raise_404)
    assert await llm.health_check() is True


@pytest.mark.asyncio
async def test_health_check_fails_on_bad_credentials(monkeypatch):
    llm = OpenAILLM(api_key="bad", model="d")

    async def raise_401():
        raise AuthenticationError("bad key", response=_response(401), body=None)

    monkeypatch.setattr(llm._client.models, "list", raise_401)
    assert await llm.health_check() is False


@pytest.mark.asyncio
async def test_health_check_fails_on_unexpected_status(monkeypatch):
    llm = OpenAILLM(api_key="k", model="d")

    async def raise_500():
        raise APIStatusError("boom", response=_response(500), body=None)

    monkeypatch.setattr(llm._client.models, "list", raise_500)
    assert await llm.health_check() is False


@pytest.mark.asyncio
async def test_health_check_fails_when_unreachable(monkeypatch):
    llm = OpenAILLM(api_key="k", model="d")

    async def raise_conn():
        raise ConnectionError("dns failure")

    monkeypatch.setattr(llm._client.models, "list", raise_conn)
    assert await llm.health_check() is False


@pytest.mark.asyncio
async def test_health_check_passes_when_models_list_works(monkeypatch):
    llm = OpenAILLM(api_key="k", model="d")

    async def ok():
        return object()

    monkeypatch.setattr(llm._client.models, "list", ok)
    assert await llm.health_check() is True


# --- api_key accepts a token provider --------------------------------------------

def test_api_key_accepts_callable_token_provider():
    """Entra ID / managed identity supplies a callable rather than a static string."""
    calls = []

    def token_provider():
        calls.append(1)
        return "token-from-provider"

    llm = OpenAILLM(api_key=token_provider, model="d")
    emb = OpenAIEmbeddings(api_key=token_provider, model="text-embedding-3-small")
    assert llm._client is not None and emb._client is not None
