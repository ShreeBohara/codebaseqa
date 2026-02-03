from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.rag.pipeline import RAGPipeline


@pytest.fixture
def rag_pipeline():
    mock_store = MagicMock()
    mock_llm = MagicMock()
    return RAGPipeline(mock_store, mock_llm, "test-repo-id")


@pytest.mark.asyncio
async def test_rag_flow(rag_pipeline):
    """Test retrieval and generation flow."""
    question = "How does auth work?"

    # Setup Mocks
    mock_chunk = MagicMock()
    mock_chunk.id = "c1"
    mock_chunk.content = "def login(): pass"
    mock_chunk.metadata = {"file_path": "auth.py", "start_line": 10, "end_line": 20}
    mock_chunk.score = 0.9

    # Mock Vector Store
    rag_pipeline._vector_store.hybrid_search = AsyncMock(return_value=[mock_chunk])
    rag_pipeline._vector_store._embedding_service.embed_query = AsyncMock(return_value=[0.1, 0.2])

    # Mock LLM
    rag_pipeline._llm.generate = AsyncMock(return_value="Auth uses JWT.")

    # 1. Test Retrieval
    retrieval_result = await rag_pipeline.retrieve(question)
    assert len(retrieval_result.chunks) == 1
    assert retrieval_result.chunks[0].file_path == "auth.py"

    # 2. Test Generation
    answer = await rag_pipeline.generate(question, retrieval_result)
    assert "Auth uses JWT." in answer

    # Verify interaction
    rag_pipeline._vector_store.hybrid_search.assert_called()
    rag_pipeline._llm.generate.assert_called()
