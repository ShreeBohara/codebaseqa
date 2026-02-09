"""Lightweight runtime migrations for incremental schema updates."""

from __future__ import annotations

import logging
from typing import List

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def _column_exists(engine: Engine, table_name: str, column_name: str) -> bool:
    inspector = inspect(engine)
    if not inspector.has_table(table_name):
        return False
    columns = inspector.get_columns(table_name)
    return any(column.get("name") == column_name for column in columns)


def _table_exists(engine: Engine, table_name: str) -> bool:
    inspector = inspect(engine)
    return inspector.has_table(table_name)


def run_pending_migrations(engine: Engine) -> List[str]:
    """
    Apply additive migrations required for backward-compatible schema hardening.
    This avoids requiring Alembic for small schema increments.
    """
    applied: List[str] = []

    with engine.begin() as connection:
        if not _column_exists(engine, "chat_messages", "retrieval_meta"):
            connection.execute(text("ALTER TABLE chat_messages ADD COLUMN retrieval_meta JSON"))
            applied.append("chat_messages.retrieval_meta")

        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_chat_messages_session_created_at "
                "ON chat_messages (session_id, created_at)"
            )
        )
        applied.append("ix_chat_messages_session_created_at")

        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_chat_sessions_repo_updated_at "
                "ON chat_sessions (repository_id, updated_at)"
            )
        )
        applied.append("ix_chat_sessions_repo_updated_at")

        if not _table_exists(engine, "learning_lessons"):
            connection.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS learning_lessons (
                        id VARCHAR(36) PRIMARY KEY,
                        repository_id VARCHAR(36) NOT NULL,
                        persona VARCHAR(50),
                        lesson_id VARCHAR(100) NOT NULL,
                        module_id VARCHAR(100),
                        lesson_json JSON NOT NULL,
                        quality_meta JSON,
                        prompt_version VARCHAR(50),
                        created_at DATETIME,
                        expires_at DATETIME,
                        FOREIGN KEY(repository_id) REFERENCES repositories(id)
                    )
                    """
                )
            )
            applied.append("learning_lessons")

        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_learning_lessons_repo_persona_lesson "
                "ON learning_lessons (repository_id, persona, lesson_id)"
            )
        )
        applied.append("ix_learning_lessons_repo_persona_lesson")

        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_learning_lessons_repo_lesson "
                "ON learning_lessons (repository_id, lesson_id)"
            )
        )
        applied.append("ix_learning_lessons_repo_lesson")

        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_learning_lessons_expiry "
                "ON learning_lessons (expires_at)"
            )
        )
        applied.append("ix_learning_lessons_expiry")

        if not _column_exists(engine, "lesson_progress", "persona"):
            connection.execute(text("ALTER TABLE lesson_progress ADD COLUMN persona VARCHAR(50)"))
            applied.append("lesson_progress.persona")

        if not _column_exists(engine, "lesson_progress", "module_id"):
            connection.execute(text("ALTER TABLE lesson_progress ADD COLUMN module_id VARCHAR(100)"))
            applied.append("lesson_progress.module_id")

        if not _column_exists(engine, "learning_syllabi", "expires_at"):
            connection.execute(text("ALTER TABLE learning_syllabi ADD COLUMN expires_at DATETIME"))
            applied.append("learning_syllabi.expires_at")

    if applied:
        logger.info("Applied runtime migrations: %s", ", ".join(applied))

    return applied
