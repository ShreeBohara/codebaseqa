from types import SimpleNamespace

import pytest

from src.core.embeddings import openai_embeddings as openai_module


class FakeRateLimitError(Exception):
    def __init__(self, headers=None):
        super().__init__("rate limited")
        self.response = SimpleNamespace(headers=headers or {})


class FakeEmbeddingsEndpoint:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    async def create(self, model: str, input):
        del model  # Unused in test doubles.
        del input
        self.calls += 1
        result = self._responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


class FakeClient:
    def __init__(self, responses):
        self.embeddings = FakeEmbeddingsEndpoint(responses)


def embedding_response(count: int) -> SimpleNamespace:
    return SimpleNamespace(
        data=[SimpleNamespace(embedding=[float(i), float(i + 1)]) for i in range(count)]
    )


@pytest.mark.asyncio
async def test_embed_texts_retries_on_rate_limit(monkeypatch):
    sleep_calls = []

    async def fake_sleep(seconds):
        sleep_calls.append(seconds)

    fake_client = FakeClient(
        [
            FakeRateLimitError(headers={"retry-after": "0.25"}),
            embedding_response(1),
        ]
    )

    monkeypatch.setattr(openai_module.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(openai_module, "RateLimitError", FakeRateLimitError)
    monkeypatch.setattr(openai_module, "AsyncOpenAI", lambda **kwargs: fake_client)

    service = openai_module.OpenAIEmbeddings(
        api_key="test",
        max_texts_per_request=1,
        request_concurrency=1,
        rate_limit_max_retries=2,
        rate_limit_base_backoff_seconds=0.01,
        rate_limit_max_backoff_seconds=1.0,
    )

    embeddings = await service.embed_texts(["hello"])

    assert len(embeddings) == 1
    assert fake_client.embeddings.calls == 2
    assert sleep_calls == [pytest.approx(0.25)]


@pytest.mark.asyncio
async def test_embed_texts_respects_min_request_spacing(monkeypatch):
    sleep_calls = []

    async def fake_sleep(seconds):
        sleep_calls.append(seconds)

    fake_client = FakeClient([embedding_response(1), embedding_response(1)])

    monkeypatch.setattr(openai_module.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(openai_module, "AsyncOpenAI", lambda **kwargs: fake_client)
    monkeypatch.setattr(openai_module.time, "monotonic", lambda: 100.0)

    service = openai_module.OpenAIEmbeddings(
        api_key="test",
        max_texts_per_request=1,
        request_concurrency=1,
        min_seconds_between_requests=0.2,
    )

    embeddings = await service.embed_texts(["first", "second"])

    assert len(embeddings) == 2
    assert fake_client.embeddings.calls == 2
    assert sleep_calls == [pytest.approx(0.2)]
