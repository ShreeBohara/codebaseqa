from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.vectorstore.chroma_store import ChromaStore, SearchResult


def test_query_normalization_removes_stopwords():
    store = ChromaStore(persist_directory="/tmp/chroma-test", embedding_service=MagicMock())
    terms = store._normalize_query_terms("What are the main features of this application?")
    assert "what" not in terms
    assert "the" not in terms
    assert "main" in terms
    assert "features" in terms


@pytest.mark.asyncio
async def test_docs_first_profile_boosts_readme_and_penalizes_trivial_exports():
    store = ChromaStore(persist_directory="/tmp/chroma-test", embedding_service=MagicMock())
    store.search = AsyncMock(
        return_value=[
            SearchResult(
                id="trivial",
                score=0.72,
                content="export {};",
                metadata={"file_path": "packages/ui/index.ts", "chunk_type": "file_summary"},
            ),
            SearchResult(
                id="docs",
                score=0.51,
                content="Documenso aims to be the world's most trusted document-signing tool.",
                metadata={"file_path": "README.md", "chunk_type": "file_summary"},
            ),
            SearchResult(
                id="manifest",
                score=0.50,
                content='{"dependencies":{"zod":"^3.0.0"}}',
                metadata={"file_path": "packages/api/package.json", "chunk_type": "file_summary"},
            ),
        ]
    )

    ranked = await store.hybrid_search(
        collection_name="repo-id",
        query_embedding=[0.1, 0.2],
        query_text="What are the main features of this application?",
        limit=3,
        profile="docs_first",
    )

    assert ranked
    assert ranked[0].metadata["file_path"] == "README.md"
    assert ranked[0].id == "docs"


@pytest.mark.asyncio
async def test_path_allowlist_filters_results():
    store = ChromaStore(persist_directory="/tmp/chroma-test", embedding_service=MagicMock())
    store.search = AsyncMock(
        return_value=[
            SearchResult(
                id="docs",
                score=0.6,
                content="Feature docs",
                metadata={"file_path": "README.md", "chunk_type": "file_summary"},
            ),
            SearchResult(
                id="code",
                score=0.7,
                content="def login(): pass",
                metadata={"file_path": "src/auth.py", "chunk_type": "function"},
            ),
        ]
    )

    ranked = await store.hybrid_search(
        collection_name="repo-id",
        query_embedding=[0.2, 0.3],
        query_text="where is auth logic",
        limit=5,
        profile="location",
        path_allowlist=["src/"],
    )

    assert len(ranked) == 1
    assert ranked[0].metadata["file_path"] == "src/auth.py"
