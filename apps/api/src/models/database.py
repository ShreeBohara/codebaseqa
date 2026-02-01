"""
Database models for CodebaseQA.
Designed for future extensibility (multi-user, teams, etc.)
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, 
    ForeignKey, Text, JSON, Index, Enum as SQLEnum
)
from sqlalchemy.orm import relationship, declarative_base
import uuid
import enum

Base = declarative_base()


class IndexingStatus(str, enum.Enum):
    PENDING = "pending"
    CLONING = "cloning"
    PARSING = "parsing"
    EMBEDDING = "embedding"
    COMPLETED = "completed"
    FAILED = "failed"


class Repository(Base):
    """Represents an indexed GitHub repository."""
    __tablename__ = "repositories"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # GitHub info
    github_url = Column(String(500), nullable=False, unique=True)
    github_owner = Column(String(255), nullable=False)
    github_name = Column(String(255), nullable=False)
    default_branch = Column(String(100), default="main")
    
    # Local storage
    local_path = Column(String(1000), nullable=True)
    
    # Indexing state
    status = Column(SQLEnum(IndexingStatus), default=IndexingStatus.PENDING)
    last_indexed_at = Column(DateTime, nullable=True)
    last_commit_sha = Column(String(40), nullable=True)
    indexing_error = Column(Text, nullable=True)
    
    # Statistics
    total_files = Column(Integer, default=0)
    total_chunks = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    
    # Metadata
    description = Column(Text, nullable=True)
    primary_language = Column(String(50), nullable=True)
    languages = Column(JSON, default=list)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    files = relationship("CodeFile", back_populates="repository", cascade="all, delete-orphan")
    chunks = relationship("CodeChunk", back_populates="repository", cascade="all, delete-orphan")
    chat_sessions = relationship("ChatSession", back_populates="repository", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_repositories_github", "github_owner", "github_name"),
        Index("ix_repositories_status", "status"),
    )


class CodeFile(Base):
    """Represents a single file in a repository."""
    __tablename__ = "code_files"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id = Column(String(36), ForeignKey("repositories.id"), nullable=False)
    
    # File info
    path = Column(String(1000), nullable=False)
    filename = Column(String(255), nullable=False)
    extension = Column(String(50), nullable=True)
    language = Column(String(50), nullable=True)
    
    # Content metadata
    size_bytes = Column(Integer, default=0)
    line_count = Column(Integer, default=0)
    content_hash = Column(String(64), nullable=True)
    
    # For Phase 2 learning paths
    imports = Column(JSON, default=list)
    exports = Column(JSON, default=list)
    dependencies = Column(JSON, default=list)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    repository = relationship("Repository", back_populates="files")
    chunks = relationship("CodeChunk", back_populates="file", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index("ix_code_files_repo_path", "repository_id", "path"),
        Index("ix_code_files_language", "language"),
    )


class CodeChunk(Base):
    """Represents a semantic chunk of code for embedding."""
    __tablename__ = "code_chunks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id = Column(String(36), ForeignKey("repositories.id"), nullable=False)
    file_id = Column(String(36), ForeignKey("code_files.id"), nullable=False)
    
    # Chunk identification
    chunk_type = Column(String(50), nullable=False)  # function, class, method
    chunk_name = Column(String(255), nullable=True)
    
    # Content
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False)
    
    # Location in file
    start_line = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)
    
    # Embedding info
    embedding_model = Column(String(100), nullable=True)
    token_count = Column(Integer, default=0)
    
    # Context
    context_before = Column(Text, nullable=True)
    docstring = Column(Text, nullable=True)
    signature = Column(String(1000), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    repository = relationship("Repository", back_populates="chunks")
    file = relationship("CodeFile", back_populates="chunks")
    
    __table_args__ = (
        Index("ix_code_chunks_repo", "repository_id"),
        Index("ix_code_chunks_file", "file_id"),
        Index("ix_code_chunks_type", "chunk_type"),
    )


class ChatSession(Base):
    """Represents a chat conversation about a repository."""
    __tablename__ = "chat_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id = Column(String(36), ForeignKey("repositories.id"), nullable=False)
    
    title = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    repository = relationship("Repository", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    """Individual message in a chat session."""
    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("chat_sessions.id"), nullable=False)
    
    role = Column(String(20), nullable=False)  # user, assistant
    content = Column(Text, nullable=False)
    
    # Retrieved context
    retrieved_chunks = Column(JSON, default=list)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("ChatSession", back_populates="messages")


class LearningPath(Base):
    """Phase 2: Generated learning paths through codebases."""
    __tablename__ = "learning_paths"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id = Column(String(36), ForeignKey("repositories.id"), nullable=False)
    
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    topic = Column(String(255), nullable=True)
    difficulty = Column(String(20), default="intermediate")
    
    steps = Column(JSON, nullable=False)
    estimated_time_minutes = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)


def init_db(engine):
    """Create all tables."""
    Base.metadata.create_all(bind=engine)
