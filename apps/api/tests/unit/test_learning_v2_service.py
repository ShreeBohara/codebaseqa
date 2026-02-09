from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace
from typing import Any, List

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config import settings
from src.models.database import Base, CodeFile, LearningLesson, LearningSyllabus, Repository
from src.models.learning import CodeReference
from src.services.learning_service import LearningService


class StubEmbeddingService:
    async def embed_query(self, query: str) -> List[float]:
        _ = query
        return [0.0]


class StubVectorStore:
    def __init__(self, docs: list[SimpleNamespace]):
        self._embedding_service = StubEmbeddingService()
        self._docs = docs

    async def search(self, collection_name: str, query_embedding: list[float], limit: int):
        _ = collection_name, query_embedding, limit
        return self._docs


class StubLLM:
    def __init__(self, response: str):
        self.response = response
        self.calls = 0

    async def generate(self, messages: list[dict[str, Any]], **kwargs):
        _ = messages, kwargs
        self.calls += 1
        return self.response


def _build_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return SessionLocal()


def _insert_repo(db, repo_id: str = "repo-1"):
    repo = Repository(
        id=repo_id,
        github_url=f"https://github.com/example/{repo_id}",
        github_owner="example",
        github_name=repo_id,
        default_branch="main",
        languages=[],
    )
    db.add(repo)
    db.commit()
    return repo


@pytest.mark.asyncio
async def test_learning_v2_persona_blueprints_cover_all_roles(monkeypatch):
    db = _build_session()
    _insert_repo(db)
    service = LearningService(db, StubLLM("{}"), StubVectorStore([]))

    monkeypatch.setattr(settings, "learning_v2_enabled", True)

    persona_ids = {p.id for p in service.get_personas()}
    assert persona_ids == {"new_hire", "auditor", "fullstack", "archaeologist"}
    assert persona_ids.issubset(set(service.PERSONA_BLUEPRINTS.keys()))


@pytest.mark.asyncio
async def test_learning_v2_curriculum_uses_cache_without_llm(monkeypatch):
    db = _build_session()
    repo = _insert_repo(db)
    now = datetime.utcnow()

    cached_payload = {
        "title": "Cached Curriculum",
        "description": "From cache",
        "modules": [
            {
                "title": "Module 1",
                "description": "Desc",
                "lessons": [
                    {"id": "lesson-1", "title": "Lesson 1", "description": "x", "type": "concept", "estimated_minutes": 10},
                    {"id": "lesson-2", "title": "Lesson 2", "description": "x", "type": "concept", "estimated_minutes": 10},
                ],
            },
            {
                "title": "Module 2",
                "description": "Desc",
                "lessons": [
                    {"id": "lesson-3", "title": "Lesson 3", "description": "x", "type": "concept", "estimated_minutes": 10},
                    {"id": "lesson-4", "title": "Lesson 4", "description": "x", "type": "concept", "estimated_minutes": 10},
                ],
            },
            {
                "title": "Module 3",
                "description": "Desc",
                "lessons": [
                    {"id": "lesson-5", "title": "Lesson 5", "description": "x", "type": "concept", "estimated_minutes": 10},
                    {"id": "lesson-6", "title": "Lesson 6", "description": "x", "type": "concept", "estimated_minutes": 10},
                ],
            },
            {
                "title": "Module 4",
                "description": "Desc",
                "lessons": [
                    {"id": "lesson-7", "title": "Lesson 7", "description": "x", "type": "concept", "estimated_minutes": 10},
                    {"id": "lesson-8", "title": "Lesson 8", "description": "x", "type": "concept", "estimated_minutes": 10},
                ],
            },
        ],
        "prompt_version": "learning_v2_1",
        "quality_meta": {"mode": "v2"},
    }
    db.add(
        LearningSyllabus(
            repository_id=repo.id,
            persona="new_hire",
            syllabus_json=cached_payload,
            created_at=now,
            expires_at=now + timedelta(days=1),
        )
    )
    db.commit()

    llm = StubLLM('{"title":"should-not-be-used"}')
    service = LearningService(db, llm, StubVectorStore([]))

    monkeypatch.setattr(settings, "learning_v2_enabled", True)
    monkeypatch.setattr(settings, "learning_cache_ttl_days", 7)

    syllabus = await service.generate_curriculum(repo.id, "new_hire")

    assert syllabus.title == "Cached Curriculum"
    assert syllabus.cache_info is not None
    assert syllabus.cache_info.source == "cache"
    assert llm.calls == 0


@pytest.mark.asyncio
async def test_learning_v2_lesson_cache_and_fallback_quality(monkeypatch):
    db = _build_session()
    repo = _insert_repo(db, "repo-2")
    now = datetime.utcnow()
    db.add(
        CodeFile(
            repository_id=repo.id,
            path="src/main.ts",
            filename="main.ts",
            extension=".ts",
            line_count=120,
            imports=[],
            exports=[],
            dependencies=[],
        )
    )
    db.add(
        LearningLesson(
            repository_id=repo.id,
            persona="new_hire",
            lesson_id="lesson-cache",
            module_id="module-1",
            lesson_json={
                "title": "Cached Lesson",
                "content_markdown": "## Mission Brief\n## Objectives\n## Architecture Walkthrough\n## Code Deep Dive\n## Pitfalls\n## Recap",
                "code_references": [
                    {"file_path": "src/main.ts", "start_line": 1, "end_line": 20, "description": "entry"}
                ],
                "persona": "new_hire",
                "module_id": "module-1",
            },
            created_at=now,
            expires_at=now + timedelta(days=1),
            prompt_version="learning_v2_1",
        )
    )
    db.commit()

    llm = StubLLM('{"content_markdown":"too short","code_references":[]}')
    docs = [SimpleNamespace(content="context", metadata={"file_path": "src/main.ts"})]
    service = LearningService(db, llm, StubVectorStore(docs))

    monkeypatch.setattr(settings, "learning_v2_enabled", True)
    monkeypatch.setattr(settings, "learning_cache_ttl_days", 7)

    cached = await service.generate_lesson(
        repo.id,
        "lesson-cache",
        "Cached Lesson",
        persona_id="new_hire",
        module_id="module-1",
    )
    assert cached is not None
    assert cached.cache_info is not None
    assert cached.cache_info.source == "cache"
    assert llm.calls == 0

    regenerated = await service.generate_lesson(
        repo.id,
        "lesson-fallback",
        "Fallback Lesson",
        persona_id="new_hire",
        module_id="module-2",
        force_regenerate=True,
    )
    assert regenerated is not None
    assert regenerated.quality_meta is not None
    assert regenerated.quality_meta.get("fallback_used") is True
    assert "Mission Brief" in regenerated.content_markdown


def test_mermaid_quality_rejects_generic_diagram_without_repo_evidence():
    db = _build_session()
    _insert_repo(db, "repo-3")
    service = LearningService(db, StubLLM("{}"), StubVectorStore([]))

    references = [
        CodeReference(
            file_path="src/lib/ai/config.ts",
            start_line=1,
            end_line=30,
            description="Primary AI configuration",
        ),
        CodeReference(
            file_path="src/lib/ai/types.ts",
            start_line=1,
            end_line=20,
            description="Type definitions for AI layer",
        ),
    ]
    generic_mermaid = "\n".join(
        [
            "flowchart LR",
            '  SYS["System"] --> PROC["Process"]',
            '  PROC --> COMP["Component"]',
            '  COMP --> OUT["Output"]',
            "  PROC --> OUT",
        ]
    )
    selected, source = service._select_high_quality_mermaid(
        raw_code=generic_mermaid,
        lesson_title="Understanding the Project Overview and Architecture",
        persona_id="new_hire",
        module_id="module-1",
        references=references,
        available_files={"src/lib/ai/config.ts", "src/lib/ai/types.ts"},
    )

    assert source == "fallback"
    assert "Referenced Code Files" in selected
    assert "config.ts" in selected or "types.ts" in selected


def test_mermaid_quality_accepts_contextual_llm_diagram():
    db = _build_session()
    _insert_repo(db, "repo-4")
    service = LearningService(db, StubLLM("{}"), StubVectorStore([]))

    references = [
        CodeReference(
            file_path="src/lib/ai/config.ts",
            start_line=1,
            end_line=30,
            description="Primary AI configuration",
        ),
    ]
    contextual_mermaid = "\n".join(
        [
            "flowchart LR",
            '  ENTRY["src/lib/ai/config.ts entry"] --> ORCH["service orchestration"]',
            '  ORCH --> CORE["core response workflow"]',
            '  CORE --> DATA["state and persistence"]',
            "  ORCH --> DATA",
        ]
    )
    selected, source = service._select_high_quality_mermaid(
        raw_code=contextual_mermaid,
        lesson_title="Understanding the Project Overview and Architecture",
        persona_id="new_hire",
        module_id="module-1",
        references=references,
        available_files={"src/lib/ai/config.ts"},
    )

    assert source == "llm"
    assert selected == contextual_mermaid
