"""
Chat endpoints with SSE streaming support.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from threading import Lock
from typing import Dict, List

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.config import settings
from src.core.demo_mode import assert_demo_repo_access
from src.core.rag.pipeline import RAGPipeline
from src.core.rate_limit import enforce_demo_soft_limit
from src.dependencies import (
    get_chat_cache,
    get_db,
    get_llm_service,
    get_vector_store,
)
from src.models.database import ChatMessage, ChatSession, Repository
from src.models.schemas import (
    ChatMessageCreate,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)

_repo_semaphores: Dict[str, asyncio.Semaphore] = {}
_repo_semaphore_lock = Lock()


def _get_repo_semaphore(repo_id: str) -> asyncio.Semaphore:
    with _repo_semaphore_lock:
        semaphore = _repo_semaphores.get(repo_id)
        if semaphore is None:
            semaphore = asyncio.Semaphore(max(1, settings.chat_max_concurrent_per_repo))
            _repo_semaphores[repo_id] = semaphore
        return semaphore


def _build_history(messages: List[ChatMessage]) -> List[Dict[str, str]]:
    max_messages = max(1, settings.chat_history_max_messages)
    token_budget = max(1, settings.chat_history_max_tokens)
    char_budget = token_budget * 4

    recent = messages[-max_messages:]
    selected: List[Dict[str, str]] = []
    used_chars = 0

    for message in reversed(recent):
        content = message.content or ""
        if not content:
            continue
        cost = len(content)
        if used_chars + cost > char_budget:
            break
        selected.append({"role": message.role, "content": content})
        used_chars += cost

    selected.reverse()
    return selected


@router.post("/sessions", response_model=ChatSessionResponse)
async def create_session(
    data: ChatSessionCreate,
    db: Session = Depends(get_db),
):
    """Create a new chat session for a repository."""
    assert_demo_repo_access(db, data.repo_id)

    repo = db.query(Repository).filter(Repository.id == data.repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    session = ChatSession(repository_id=data.repo_id)
    db.add(session)
    db.commit()
    db.refresh(session)

    return ChatSessionResponse(
        id=session.id,
        repo_id=session.repository_id,
        title=session.title,
        messages=[],
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_session(
    session_id: str,
    db: Session = Depends(get_db),
):
    """Get chat session with all messages."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    assert_demo_repo_access(db, session.repository_id)

    ordered_messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )

    messages = [
        ChatMessageResponse(
            id=m.id,
            role=m.role,
            content=m.content,
            retrieved_chunks=m.retrieved_chunks,
            retrieval_meta=m.retrieval_meta,
            created_at=m.created_at,
        )
        for m in ordered_messages
    ]

    return ChatSessionResponse(
        id=session.id,
        repo_id=session.repository_id,
        title=session.title,
        messages=messages,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: str,
    message: ChatMessageCreate,
    request: Request,
    db: Session = Depends(get_db),
    llm_service=Depends(get_llm_service),
    vector_store=Depends(get_vector_store),
    chat_cache=Depends(get_chat_cache),
):
    """Send message and get streaming response."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    assert_demo_repo_access(db, session.repository_id)
    await enforce_demo_soft_limit(request, "chat")

    # Build history from persisted messages using explicit ordering.
    prior_messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    history = _build_history(prior_messages)

    # Save user message before generation.
    user_msg = ChatMessage(session_id=session_id, role="user", content=message.content)
    db.add(user_msg)
    db.commit()
    db.refresh(user_msg)

    # Update title from first message.
    if not session.title:
        session.title = message.content[:100]
        db.commit()

    rag = RAGPipeline(
        vector_store=vector_store,
        llm_service=llm_service,
        repo_id=session.repository_id,
        chat_cache=chat_cache,
    )

    async def generate_stream():
        full_response = ""
        retrieved_chunks = []
        retrieval_meta = {}
        semaphore = _get_repo_semaphore(session.repository_id)
        acquired = False

        try:
            # Per-repository concurrency guard.
            try:
                await asyncio.wait_for(
                    semaphore.acquire(),
                    timeout=max(0.1, float(settings.chat_concurrency_wait_seconds)),
                )
                acquired = True
            except TimeoutError:
                payload = {
                    "type": "error",
                    "error": "Chat queue is busy for this repository. Please retry shortly.",
                    "code": "CHAT_REPO_CONCURRENCY_LIMIT",
                }
                yield f"data: {json.dumps(payload)}\n\n"
                return

            async with asyncio.timeout(max(5, int(settings.chat_request_timeout_seconds))):
                retrieve_started = time.perf_counter()
                context = await rag.retrieve(
                    query=message.content,
                    mode=message.mode or "auto",
                    context_files=message.context_files,
                )
                retrieved_chunks = context.chunks
                retrieve_elapsed_ms = (time.perf_counter() - retrieve_started) * 1000

                sources = [
                    {
                        "file": chunk.file_path,
                        "content": chunk.content[:240],
                        "start_line": chunk.start_line,
                        "end_line": chunk.end_line,
                        "score": chunk.score,
                    }
                    for chunk in retrieved_chunks[:6]
                ]
                yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"

                retrieval_meta = {
                    "intent": context.intent,
                    "profile": context.profile,
                    "grounding": context.diagnostics.grounding,
                    "retrieval": {
                        "queries": context.diagnostics.expanded_queries,
                        "candidate_count": context.diagnostics.candidate_count,
                        "reranked": context.diagnostics.reranked,
                        "cache_hit": context.diagnostics.cache_hit,
                        "retrieval_time_ms": round(context.diagnostics.retrieval_time_ms, 2),
                        "rerank_time_ms": round(context.diagnostics.rerank_time_ms, 2),
                        "router_time_ms": round(retrieve_elapsed_ms, 2),
                    },
                    "context_files": message.context_files or [],
                    "mode": message.mode or "auto",
                }

                if settings.chat_emit_meta_event:
                    meta_payload = {
                        "type": "meta",
                        "meta": {
                            "intent": context.intent,
                            "profile": context.profile,
                            "grounding": context.diagnostics.grounding,
                            "latency_ms": {
                                "retrieval": round(context.diagnostics.retrieval_time_ms, 2),
                                "rerank": round(context.diagnostics.rerank_time_ms, 2),
                            },
                        },
                    }
                    if message.debug:
                        meta_payload["meta"]["debug"] = retrieval_meta
                    yield f"data: {json.dumps(meta_payload)}\n\n"

                async for token in rag.generate_stream(
                    query=message.content,
                    context=context,
                    history=history,
                ):
                    full_response += token
                    yield f"data: {json.dumps({'type': 'content', 'content': token})}\n\n"

                assistant_msg = ChatMessage(
                    session_id=session_id,
                    role="assistant",
                    content=full_response,
                    retrieved_chunks=[{"id": chunk.id, "file": chunk.file_path} for chunk in retrieved_chunks],
                    retrieval_meta=retrieval_meta,
                )
                db.add(assistant_msg)
                db.commit()

                yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except TimeoutError:
            payload = {
                "type": "error",
                "error": "Chat request timed out while generating a response.",
                "code": "CHAT_REQUEST_TIMEOUT",
            }
            yield f"data: {json.dumps(payload)}\n\n"
        except Exception as exc:
            logger.exception("Chat generation failed for session=%s", session_id)
            payload = {"type": "error", "error": str(exc), "code": "CHAT_GENERATION_ERROR"}
            yield f"data: {json.dumps(payload)}\n\n"
        finally:
            if acquired:
                semaphore.release()

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
