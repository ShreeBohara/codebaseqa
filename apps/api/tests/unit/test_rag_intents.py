from unittest.mock import AsyncMock, MagicMock

import pytest

from src.core.rag.pipeline import ChatIntent, RAGPipeline


@pytest.fixture
def rag_pipeline():
    mock_store = MagicMock()
    mock_store._embedding_service = MagicMock()
    mock_llm = MagicMock()
    mock_llm.generate = AsyncMock(return_value="overview")
    return RAGPipeline(mock_store, mock_llm, "test-repo-id")


def test_classify_overview_intent(rag_pipeline):
    query = "What are the main features of this application?"
    assert rag_pipeline.classify_intent(query) == ChatIntent.OVERVIEW


def test_classify_implementation_intent(rag_pipeline):
    query = "How does authentication and authorization work?"
    assert rag_pipeline.classify_intent(query) == ChatIntent.IMPLEMENTATION


def test_classify_tech_stack_intent(rag_pipeline):
    query = "What technologies and libraries are used in this stack?"
    assert rag_pipeline.classify_intent(query) == ChatIntent.TECH_STACK


def test_classify_location_intent(rag_pipeline):
    query = "Where is the user session validation logic defined?"
    assert rag_pipeline.classify_intent(query) == ChatIntent.LOCATION


def test_classify_troubleshooting_intent(rag_pipeline):
    query = "Why does this route throw an exception in production?"
    assert rag_pipeline.classify_intent(query) == ChatIntent.TROUBLESHOOTING


@pytest.mark.asyncio
async def test_llm_tiebreak_for_ambiguous_intent(rag_pipeline):
    rag_pipeline._llm.generate = AsyncMock(return_value="tech_stack")
    rag_pipeline._score_intents = MagicMock(
        return_value=[
            (ChatIntent.OVERVIEW, 3),
            (ChatIntent.TECH_STACK, 3),
            (ChatIntent.IMPLEMENTATION, 1),
        ]
    )
    query = "Give me an overview of the technologies used here"
    intent = await rag_pipeline.classify_intent_async(query)
    assert intent == ChatIntent.TECH_STACK


@pytest.mark.asyncio
async def test_mode_override(rag_pipeline):
    query = "How does auth work?"
    intent = await rag_pipeline.classify_intent_async(query, mode="overview")
    assert intent == ChatIntent.OVERVIEW
