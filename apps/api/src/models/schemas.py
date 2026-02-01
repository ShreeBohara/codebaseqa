"""
Pydantic schemas for API request/response validation.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl
from enum import Enum


# Enums
class IndexingStatus(str, Enum):
    PENDING = "pending"
    CLONING = "cloning"
    PARSING = "parsing"
    EMBEDDING = "embedding"
    COMPLETED = "completed"
    FAILED = "failed"


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChunkType(str, Enum):
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    MODULE = "module"


# Repository Schemas
class RepoCreate(BaseModel):
    """Request to index a new repository."""
    github_url: HttpUrl = Field(..., examples=["https://github.com/owner/repo"])
    branch: Optional[str] = Field(None, examples=["main"])


class RepoResponse(BaseModel):
    """Repository information response."""
    id: str
    github_url: str
    github_owner: str
    github_name: str
    status: IndexingStatus
    description: Optional[str] = None
    primary_language: Optional[str] = None
    languages: List[str] = []
    total_files: int = 0
    total_chunks: int = 0
    last_indexed_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class RepoListResponse(BaseModel):
    """List of repositories."""
    repositories: List[RepoResponse]
    total: int


class IndexingProgress(BaseModel):
    """Real-time indexing progress update."""
    repo_id: str
    status: IndexingStatus
    progress_percent: float = Field(..., ge=0, le=100)
    current_step: str
    files_processed: int = 0
    total_files: int = 0
    error: Optional[str] = None


# Chat Schemas
class ChatMessageCreate(BaseModel):
    """User message input."""
    content: str = Field(..., min_length=1, max_length=10000)
    context_files: Optional[List[str]] = Field(None, description="Specific files to focus on")


class ChatMessageResponse(BaseModel):
    """Chat message response."""
    id: str
    role: MessageRole
    content: str
    retrieved_chunks: Optional[List[Dict[str, Any]]] = None
    created_at: datetime


class ChatSessionCreate(BaseModel):
    """Create a new chat session."""
    repo_id: str


class ChatSessionResponse(BaseModel):
    """Chat session with messages."""
    id: str
    repo_id: str
    title: Optional[str] = None
    messages: List[ChatMessageResponse] = []
    created_at: datetime
    updated_at: datetime


class StreamingChunk(BaseModel):
    """Server-sent event chunk for streaming responses."""
    type: str  # "content", "sources", "done", "error"
    content: Optional[str] = None
    sources: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


# Search Schemas
class SearchQuery(BaseModel):
    """Search query input."""
    query: str = Field(..., min_length=1, max_length=1000)
    repo_id: str
    limit: int = Field(10, ge=1, le=50)
    file_filter: Optional[List[str]] = None
    language_filter: Optional[List[str]] = None


class SearchResult(BaseModel):
    """Individual search result."""
    chunk_id: str
    file_path: str
    content: str
    chunk_type: ChunkType
    score: float
    start_line: int
    end_line: int
    highlights: Optional[List[str]] = None


class SearchResponse(BaseModel):
    """Search results response."""
    results: List[SearchResult]
    total: int
    query_time_ms: float


# Learning Path Schemas (Phase 2)
class LearningPathStep(BaseModel):
    """Single step in a learning path."""
    order: int
    file_path: str
    chunk_id: Optional[str] = None
    title: str
    explanation: str
    code_snippet: Optional[str] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None


class LearningPathCreate(BaseModel):
    """Request to generate a learning path."""
    repo_id: str
    topic: str = Field(..., examples=["authentication flow"])
    difficulty: str = Field("intermediate", pattern="^(beginner|intermediate|advanced)$")


class LearningPathResponse(BaseModel):
    """Generated learning path."""
    id: str
    repo_id: str
    title: str
    description: str
    topic: str
    difficulty: str
    steps: List[LearningPathStep]
    estimated_time_minutes: int
    created_at: datetime
