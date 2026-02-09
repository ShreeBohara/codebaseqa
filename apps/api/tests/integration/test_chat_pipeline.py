import json
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.core.cache.chat_cache import ChatCache
from src.core.rag.pipeline import RetrievalDiagnostics, RetrievalResult, RetrievedChunk
from src.dependencies import get_chat_cache, get_db, get_llm_service, get_vector_store
from src.models.database import ChatMessage, ChatSession


class _FakeQuery:
    def __init__(self, first_obj=None, all_objs=None):
        self._first_obj = first_obj
        self._all_objs = all_objs or []

    def filter(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def first(self):
        return self._first_obj

    def all(self):
        return list(self._all_objs)


class _FakeDB:
    def __init__(self):
        self.session = SimpleNamespace(
            id="session-1",
            repository_id="repo-1",
            title=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.chat_history = []
        self.saved_messages = []

    def query(self, model):
        if model is ChatSession:
            return _FakeQuery(first_obj=self.session)
        if model is ChatMessage:
            return _FakeQuery(first_obj=None, all_objs=self.chat_history)
        raise AssertionError(f"Unexpected model query: {model}")

    def add(self, obj):
        self.saved_messages.append(obj)
        if isinstance(obj, ChatMessage):
            self.chat_history.append(obj)

    def commit(self):
        return None

    def refresh(self, obj):
        if not getattr(obj, "id", None):
            obj.id = f"msg-{len(self.saved_messages)}"
        if not getattr(obj, "created_at", None):
            obj.created_at = datetime.utcnow()


class _FakeRAG:
    last_retrieve_kwargs = {}

    def __init__(self, *args, **kwargs):
        pass

    async def retrieve(self, query: str, mode: str = "auto", context_files=None):
        _FakeRAG.last_retrieve_kwargs = {
            "query": query,
            "mode": mode,
            "context_files": context_files,
        }
        chunk = RetrievedChunk(
            id="chunk-1",
            content="Documenso aims to be the world's most trusted document-signing tool.",
            file_path="README.md",
            start_line=30,
            end_line=45,
            chunk_type="file_summary",
            chunk_name="README.md",
            score=0.95,
        )
        diagnostics = RetrievalDiagnostics(
            intent="overview",
            profile="docs_first",
            expanded_queries=[query, f"{query} README overview"],
            candidate_count=8,
            reranked=True,
            retrieval_time_ms=12.5,
            rerank_time_ms=4.2,
            cache_hit=False,
            grounding="high",
        )
        return RetrievalResult(
            chunks=[chunk],
            query=query,
            intent="overview",
            profile="docs_first",
            diagnostics=diagnostics,
        )

    async def generate_stream(self, query: str, context: RetrievalResult, history=None):
        yield "Documenso is an open-source document signing platform."


def _collect_sse_events(response_text: str):
    events = []
    for line in response_text.splitlines():
        if line.startswith("data: "):
            events.append(json.loads(line[6:]))
    return events


@pytest.mark.parametrize("debug_flag", [False, True])
def test_chat_stream_emits_sources_meta_content_done(client, monkeypatch, debug_flag):
    from src.api.routes import chat as chat_route

    fake_db = _FakeDB()
    monkeypatch.setattr(chat_route, "RAGPipeline", _FakeRAG)

    app_client = client
    app_client.app.dependency_overrides[get_db] = lambda: fake_db
    app_client.app.dependency_overrides[get_llm_service] = lambda: MagicMock()
    app_client.app.dependency_overrides[get_vector_store] = lambda: MagicMock()
    app_client.app.dependency_overrides[get_chat_cache] = lambda: ChatCache()

    response = app_client.post(
        "/api/chat/sessions/session-1/messages",
        json={
            "content": "What are the main features of this application?",
            "mode": "overview",
            "debug": debug_flag,
            "context_files": ["README.md"],
        },
    )

    assert response.status_code == 200
    events = _collect_sse_events(response.text)
    event_types = [event.get("type") for event in events]
    assert "sources" in event_types
    assert "meta" in event_types
    assert "content" in event_types
    assert "done" in event_types

    meta_event = next(event for event in events if event.get("type") == "meta")
    assert meta_event["meta"]["intent"] == "overview"
    assert meta_event["meta"]["profile"] == "docs_first"
    assert meta_event["meta"]["grounding"] == "high"

    sources_event = next(event for event in events if event.get("type") == "sources")
    assert sources_event["sources"][0]["file"] == "README.md"

    assistant_messages = [msg for msg in fake_db.saved_messages if getattr(msg, "role", "") == "assistant"]
    assert assistant_messages
    assert assistant_messages[-1].retrieval_meta["intent"] == "overview"

    app_client.app.dependency_overrides.clear()


def test_chat_passes_mode_and_context_files_to_rag(client, monkeypatch):
    from src.api.routes import chat as chat_route

    fake_db = _FakeDB()
    monkeypatch.setattr(chat_route, "RAGPipeline", _FakeRAG)

    app_client = client
    app_client.app.dependency_overrides[get_db] = lambda: fake_db
    app_client.app.dependency_overrides[get_llm_service] = lambda: MagicMock()
    app_client.app.dependency_overrides[get_vector_store] = lambda: MagicMock()
    app_client.app.dependency_overrides[get_chat_cache] = lambda: ChatCache()

    response = app_client.post(
        "/api/chat/sessions/session-1/messages",
        json={
            "content": "What are the main features of this application?",
            "mode": "overview",
            "context_files": ["README.md", "docs/"],
        },
    )

    assert response.status_code == 200
    assert _FakeRAG.last_retrieve_kwargs["mode"] == "overview"
    assert _FakeRAG.last_retrieve_kwargs["context_files"] == ["README.md", "docs/"]

    app_client.app.dependency_overrides.clear()
