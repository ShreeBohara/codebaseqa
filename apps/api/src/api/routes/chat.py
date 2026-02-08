"""
Chat endpoints with SSE streaming support.
"""

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.core.demo_mode import assert_demo_repo_access
from src.core.rate_limit import enforce_demo_soft_limit
from src.core.rag.pipeline import RAGPipeline
from src.dependencies import get_db, get_llm_service, get_vector_store
from src.models.database import ChatMessage, ChatSession, Repository
from src.models.schemas import (
    ChatMessageCreate,
    ChatMessageResponse,
    ChatSessionCreate,
    ChatSessionResponse,
)

router = APIRouter()


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

    messages = [
        ChatMessageResponse(
            id=m.id,
            role=m.role,
            content=m.content,
            retrieved_chunks=m.retrieved_chunks,
            created_at=m.created_at,
        )
        for m in session.messages
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
    llm_service = Depends(get_llm_service),
    vector_store = Depends(get_vector_store),
):
    """Send message and get streaming response."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    assert_demo_repo_access(db, session.repository_id)
    enforce_demo_soft_limit(request, "chat")

    # Save user message
    user_msg = ChatMessage(session_id=session_id, role="user", content=message.content)
    db.add(user_msg)
    db.commit()

    # Update title from first message
    if not session.title:
        session.title = message.content[:100]
        db.commit()

    # Build history - limit to last 20 messages to avoid context overflow
    recent_messages = session.messages[-21:-1] if len(session.messages) > 21 else session.messages[:-1]
    history = [{"role": m.role, "content": m.content} for m in recent_messages]

    # RAG pipeline
    rag = RAGPipeline(
        vector_store=vector_store,
        llm_service=llm_service,
        repo_id=session.repository_id,
    )

    async def generate_stream():
        full_response = ""
        retrieved_chunks = []

        try:
            # Retrieve context
            context = await rag.retrieve(query=message.content)
            retrieved_chunks = context.chunks

            # Send sources first
            sources = [
                {
                    "file": c.file_path,
                    "content": c.content[:200],
                    "start_line": c.start_line,
                    "end_line": c.end_line,
                    "score": c.score
                }
                for c in retrieved_chunks[:5]
            ]
            yield f"data: {json.dumps({'type': 'sources', 'sources': sources})}\n\n"

            # Stream response
            async for token in rag.generate_stream(query=message.content, context=context, history=history):
                full_response += token
                yield f"data: {json.dumps({'type': 'content', 'content': token})}\n\n"

            # Save assistant message
            assistant_msg = ChatMessage(
                session_id=session_id,
                role="assistant",
                content=full_response,
                retrieved_chunks=[{"id": c.id, "file": c.file_path} for c in retrieved_chunks]
            )
            db.add(assistant_msg)
            db.commit()

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )
