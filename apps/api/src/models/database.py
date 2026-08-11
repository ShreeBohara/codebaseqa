"""
Database models for CodebaseQA.
Designed for future extensibility (multi-user, teams, etc.)
"""

import enum
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import declarative_base, relationship

logger = logging.getLogger(__name__)

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
    # Cascade matters: without it, DELETE /api/repos/{id} would leave orphaned edges
    # behind, and a later re-import of the same repo would union old and new graphs.
    dependencies = relationship(
        "CodeDependency", back_populates="repository", cascade="all, delete-orphan"
    )

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


class CodeDependency(Base):
    """
    A resolved import edge between two files, derived once at index time.

    Exists because graph generation used to re-derive every edge on each cache miss by
    reading every source file off disk inside the request path (see
    LearningService._build_deterministic_edges). That made graph latency proportional to
    repository size, put blocking file I/O on the event loop, and coupled the graph to
    the clone still being present -- which breaks after a redeploy or container restart.

    Derivation now happens once per index, while the clone definitely exists, and the
    read path is a single indexed query.
    """
    __tablename__ = "code_dependencies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id = Column(String(36), ForeignKey("repositories.id"), nullable=False)

    # Repo-relative paths, matching CodeFile.path so they can be joined or mapped.
    source_path = Column(String(1000), nullable=False)
    target_path = Column(String(1000), nullable=False)

    # How the edge was classified (_infer_relation) and how much to trust it
    # (_build_deterministic_edges): relative imports score higher than bare specifiers.
    relation = Column(String(50), nullable=False, default="imports")
    weight = Column(Integer, default=1)
    confidence = Column(Float, default=0.72)

    # The raw specifier that produced this edge, kept for debugging why an edge exists.
    specifier = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    repository = relationship("Repository", back_populates="dependencies")

    __table_args__ = (
        # The read path always filters by repository first.
        Index("ix_code_dependencies_repo", "repository_id"),
        Index("ix_code_dependencies_repo_source", "repository_id", "source_path"),
        Index("ix_code_dependencies_repo_target", "repository_id", "target_path"),
        UniqueConstraint(
            "repository_id", "source_path", "target_path", "relation",
            name="uq_code_dependencies_edge",
        ),
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

    __table_args__ = (
        Index("ix_chat_sessions_repo_updated_at", "repository_id", "updated_at"),
    )


class ChatMessage(Base):
    """Individual message in a chat session."""
    __tablename__ = "chat_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("chat_sessions.id"), nullable=False)

    role = Column(String(20), nullable=False)  # user, assistant
    content = Column(Text, nullable=False)

    # Retrieved context
    retrieved_chunks = Column(JSON, default=list)
    retrieval_meta = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    session = relationship("ChatSession", back_populates="messages")

    __table_args__ = (
        Index("ix_chat_messages_session_created_at", "session_id", "created_at"),
    )


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


class LearningSyllabus(Base):
    """Cached syllabus to avoid regeneration."""
    __tablename__ = "learning_syllabi"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id = Column(String(36), ForeignKey("repositories.id"), nullable=False)

    persona = Column(String(50), nullable=False)
    syllabus_json = Column(JSON, nullable=False)  # Full syllabus data

    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)  # Regenerate after expiry

    __table_args__ = (
        Index("ix_learning_syllabi_repo_persona", "repository_id", "persona"),
    )


class LearningLesson(Base):
    """Cached lesson payloads to avoid regeneration."""
    __tablename__ = "learning_lessons"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id = Column(String(36), ForeignKey("repositories.id"), nullable=False)

    persona = Column(String(50), nullable=True)
    lesson_id = Column(String(100), nullable=False)
    module_id = Column(String(100), nullable=True)
    lesson_json = Column(JSON, nullable=False)
    quality_meta = Column(JSON, nullable=True)
    prompt_version = Column(String(50), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_learning_lessons_repo_persona_lesson", "repository_id", "persona", "lesson_id"),
        Index("ix_learning_lessons_repo_lesson", "repository_id", "lesson_id"),
        Index("ix_learning_lessons_expiry", "expires_at"),
    )


class LessonProgress(Base):
    """Track lesson completion per repository."""
    __tablename__ = "lesson_progress"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id = Column(String(36), ForeignKey("repositories.id"), nullable=False)

    lesson_id = Column(String(100), nullable=False)
    module_id = Column(String(100), nullable=True)
    persona = Column(String(50), nullable=True)

    status = Column(String(20), default="not_started")  # not_started, in_progress, completed

    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    time_spent_seconds = Column(Integer, default=0)

    # Quiz performance
    quiz_score = Column(Float, nullable=True)  # 0.0 - 1.0
    quiz_attempts = Column(Integer, default=0)

    # Challenge performance
    challenges_completed = Column(Integer, default=0)
    challenges_perfect = Column(Integer, default=0)  # No hints used

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_lesson_progress_repo", "repository_id"),
        Index("ix_lesson_progress_lesson", "repository_id", "lesson_id"),
    )


class UserXP(Base):
    """XP and level tracking per repository."""
    __tablename__ = "user_xp"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id = Column(String(36), ForeignKey("repositories.id"), nullable=False, unique=True)

    total_xp = Column(Integer, default=0)
    level = Column(Integer, default=1)

    # Streak tracking
    streak_days = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_activity_date = Column(DateTime, nullable=True)

    # Statistics
    lessons_completed = Column(Integer, default=0)
    quizzes_passed = Column(Integer, default=0)
    challenges_completed = Column(Integer, default=0)
    perfect_quizzes = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Achievement(Base):
    """Unlocked achievements per repository."""
    __tablename__ = "achievements"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id = Column(String(36), ForeignKey("repositories.id"), nullable=False)

    achievement_key = Column(String(50), nullable=False)  # e.g., "first_lesson", "streak_7"
    category = Column(String(30), nullable=True)  # learning, streak, explorer, challenge

    unlocked_at = Column(DateTime, default=datetime.utcnow)
    xp_awarded = Column(Integer, default=0)

    __table_args__ = (
        Index("ix_achievements_repo", "repository_id"),
        Index("ix_achievements_key", "repository_id", "achievement_key", unique=True),
    )


class GraphNodeInteraction(Base):
    """Unique graph node views for graph exploration achievements."""
    __tablename__ = "graph_node_interactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    repository_id = Column(String(36), ForeignKey("repositories.id"), nullable=False)
    node_id = Column(String(1000), nullable=False)
    viewed_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_graph_node_interactions_repo", "repository_id"),
        Index("ix_graph_node_interactions_repo_node", "repository_id", "node_id", unique=True),
    )


def reap_stuck_indexing(engine) -> int:
    """
    Fail repositories left mid-index by a process that died.

    Only FAILED and COMPLETED are terminal. A container killed during CLONING, PARSING or
    EMBEDDING left the row in that state forever, and the only self-healing path in
    repos.py and seed_demo.py triggers on FAILED -- so a stuck repository could never be
    retried through the API, and in demo mode that bricked the deployment.

    Runs at startup, where anything still in a transient state provably has no live
    indexer, because the process that owned it is gone.
    """
    from sqlalchemy import text as _text

    transient = ("cloning", "parsing", "embedding")
    with engine.begin() as connection:
        placeholders = ", ".join(f":s{i}" for i in range(len(transient)))
        params = {f"s{i}": value for i, value in enumerate(transient)}
        # SQLEnum persists the member NAME, so compare case-insensitively to be safe
        # across both spellings.
        result = connection.execute(
            _text(
                "UPDATE repositories SET status = 'FAILED', "
                "indexing_error = COALESCE(indexing_error, "
                "'Indexing was interrupted before completing. Re-import to retry.') "
                f"WHERE LOWER(status) IN ({placeholders})"
            ),
            params,
        )
        reaped = result.rowcount or 0

    if reaped:
        logger.warning(
            "Marked %d repository(ies) as failed: they were mid-index when the previous "
            "process exited. They can now be re-indexed.", reaped
        )
    return reaped


def init_db(engine):
    """Create all tables."""
    Base.metadata.create_all(bind=engine)
