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


def _add_column(connection, table: str, column: str, ddl: str, applied: List[str]) -> None:
    """
    Add a column idempotently, tolerating a concurrent process adding it first.

    SQLite has no ADD COLUMN IF NOT EXISTS, so the only option is check-then-act -- which
    is a race: two replicas starting together both see the column missing and both issue
    the ALTER, and the loser fails with "duplicate column name". That took down the second
    replica's startup entirely.

    Rather than serialize startup with a lock (a lock file is unreliable on a shared
    volume, and a DB-level mutex needs its own release path), the operation is made
    genuinely idempotent: a duplicate-column error means someone else applied it, which is
    success. Every other error still propagates.
    """
    from sqlalchemy.exc import OperationalError, ProgrammingError

    try:
        connection.execute(text(ddl))
        applied.append(f"{table}.{column}")
    except (OperationalError, ProgrammingError) as exc:
        message = str(exc).lower()
        if "duplicate column" in message or "already exists" in message:
            logger.debug(
                "Column %s.%s already added by another process; continuing", table, column
            )
            return
        raise


def run_pending_migrations(engine: Engine) -> List[str]:
    """
    Apply additive migrations required for backward-compatible schema hardening.
    This avoids requiring Alembic for small schema increments.
    """
    applied: List[str] = []

    with engine.begin() as connection:
        _add_column(
            connection, "chat_messages", "retrieval_meta",
            "ALTER TABLE chat_messages ADD COLUMN retrieval_meta JSON", applied,
        )

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

        _add_column(
            connection, "lesson_progress", "persona",
            "ALTER TABLE lesson_progress ADD COLUMN persona VARCHAR(50)", applied,
        )

        _add_column(
            connection, "lesson_progress", "module_id",
            "ALTER TABLE lesson_progress ADD COLUMN module_id VARCHAR(100)", applied,
        )

        _add_column(
            connection, "learning_syllabi", "expires_at",
            "ALTER TABLE learning_syllabi ADD COLUMN expires_at DATETIME", applied,
        )

        # code_dependencies itself is created by init_db/create_all, which runs first
        # (main.py). These indexes are declared on the model too, so this block only
        # matters for a database that predates the table and gets it via create_all
        # without the accompanying indexes -- it is idempotent either way.
        connection.execute(
            text(
                "CREATE INDEX IF NOT EXISTS ix_code_dependencies_repo "
                "ON code_dependencies (repository_id)"
            )
        )
        applied.append("ix_code_dependencies_repo")

    if applied:
        logger.info("Applied runtime migrations: %s", ", ".join(applied))

    return applied
