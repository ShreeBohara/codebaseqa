"""
Shared indexing-progress store, and the stuck-index reaper.

Both fix bugs where the failure mode was silence rather than an error:

  * progress written to a per-instance dict was invisible to the SSE endpoint, which
    builds its own IndexingService -- so the bar could only show 0% or 100%.
  * a container killed mid-index left the repository in CLONING/PARSING/EMBEDDING
    forever, and every self-healing path keys on FAILED, so it could never be retried.

Redis is exercised with fakeredis, which implements streams, consumer groups and
XAUTOCLAIM, so the Redis path here is genuinely executed rather than mocked.
"""

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from src.core.progress import ProgressStore
from src.models.database import Base, IndexingStatus, Repository, reap_stuck_indexing


@pytest.fixture()
def redis_client():
    import fakeredis.aioredis

    return fakeredis.aioredis.FakeRedis()


@pytest.fixture(autouse=True)
def _clear_memory():
    """The in-memory fallback is process-wide by design, so isolate tests from it."""
    import src.core.progress as mod

    mod._MEMORY.clear()
    yield
    mod._MEMORY.clear()


# --- the bug this replaces -------------------------------------------------------

@pytest.mark.asyncio
async def test_progress_is_visible_across_store_instances(redis_client):
    """
    The actual defect: the reader is a different object from the writer. A per-instance
    dict cannot satisfy this, which is why the SSE endpoint always fell back to the
    database branch and reported "Unknown" at 0%.
    """
    writer = ProgressStore(redis_client)
    reader = ProgressStore(redis_client)

    await writer.publish("repo-1", "parsing", "Parsing app.ts...", 42.5, 17, 40)

    event = await reader.latest("repo-1")
    assert event is not None, "a separate instance must observe the write"
    assert event["status"] == "parsing"
    assert event["current_step"] == "Parsing app.ts..."
    assert event["progress_percent"] == 42.5
    assert event["files_processed"] == 17
    assert event["total_files"] == 40


@pytest.mark.asyncio
async def test_memory_fallback_also_shares_across_instances():
    """With no Redis the store must still work within one process (the local-dev shape)."""
    writer, reader = ProgressStore(None), ProgressStore(None)
    assert writer.backend == "memory"

    await writer.publish("repo-2", "embedding", "Generating embeddings...", 80)
    event = await reader.latest("repo-2")
    assert event["status"] == "embedding"
    assert event["progress_percent"] == 80


@pytest.mark.asyncio
async def test_backend_reports_which_path_is_live(redis_client):
    assert ProgressStore(redis_client).backend == "redis"
    assert ProgressStore(None).backend == "memory"


# --- history / replay -----------------------------------------------------------

@pytest.mark.asyncio
async def test_history_is_oldest_first_so_a_late_client_can_replay(redis_client):
    store = ProgressStore(redis_client)
    for pct, step in ((0, "Cloning"), (20, "Parsing"), (80, "Embedding"), (100, "Done")):
        await store.publish("repo-3", "working", step, pct)

    history = await store.history("repo-3")
    assert [e["progress_percent"] for e in history] == [0, 20, 80, 100]


@pytest.mark.asyncio
async def test_latest_returns_none_before_anything_is_published(redis_client):
    assert await ProgressStore(redis_client).latest("never-seen") is None


@pytest.mark.asyncio
async def test_clear_removes_progress(redis_client):
    store = ProgressStore(redis_client)
    await store.publish("repo-4", "parsing", "x", 10)
    await store.clear("repo-4")
    assert await store.latest("repo-4") is None


# --- resilience: progress must never break indexing -----------------------------

class ExplodingRedis:
    async def xadd(self, *a, **k):
        raise RuntimeError("redis down")

    async def xrevrange(self, *a, **k):
        raise RuntimeError("redis down")

    async def xrange(self, *a, **k):
        raise RuntimeError("redis down")

    async def delete(self, *a, **k):
        raise RuntimeError("redis down")


@pytest.mark.asyncio
async def test_a_broken_redis_degrades_to_memory_instead_of_raising():
    """
    Progress is telemetry. If publishing it could raise, a Redis blip would fail an
    otherwise healthy index -- so the event falls back to memory and the caller never
    sees an exception.
    """
    store = ProgressStore(ExplodingRedis())

    await store.publish("repo-5", "parsing", "still working", 33)

    event = await store.latest("repo-5")
    assert event is not None, "the event should have landed in the memory fallback"
    assert event["progress_percent"] == 33
    assert await store.history("repo-5")
    await store.clear("repo-5")


# --- stuck-index reaper ---------------------------------------------------------

@pytest.fixture()
def engine(tmp_path):
    eng = create_engine(f"sqlite:///{tmp_path / 'reap.db'}")
    Base.metadata.create_all(eng)
    return eng


def _add(engine, name, status):
    db = sessionmaker(bind=engine)()
    db.add(Repository(
        github_url=f"https://github.com/o/{name}", github_owner="o",
        github_name=name, status=status,
    ))
    db.commit()
    db.close()


def _status_of(engine, name):
    with engine.begin() as c:
        row = c.execute(
            text("SELECT status FROM repositories WHERE github_name = :n"), {"n": name}
        ).first()
    return (row[0] or "").lower()


@pytest.mark.parametrize(
    "stuck", [IndexingStatus.CLONING, IndexingStatus.PARSING, IndexingStatus.EMBEDDING]
)
def test_transient_states_are_reaped_to_failed(engine, stuck):
    _add(engine, f"r-{stuck.value}", stuck)
    assert reap_stuck_indexing(engine) == 1
    assert _status_of(engine, f"r-{stuck.value}") == "failed"


@pytest.mark.parametrize(
    "keep", [IndexingStatus.COMPLETED, IndexingStatus.PENDING, IndexingStatus.FAILED]
)
def test_terminal_and_pending_states_are_left_alone(engine, keep):
    """
    PENDING must survive: a repository queued by a background task that has not started
    yet is not stuck, and failing it would break the normal import path.
    """
    _add(engine, f"k-{keep.value}", keep)
    assert reap_stuck_indexing(engine) == 0
    assert _status_of(engine, f"k-{keep.value}") == keep.value


def test_reaper_sets_an_actionable_error_message(engine):
    _add(engine, "msg", IndexingStatus.PARSING)
    reap_stuck_indexing(engine)
    with engine.begin() as c:
        err = c.execute(
            text("SELECT indexing_error FROM repositories WHERE github_name = 'msg'")
        ).scalar()
    assert err and "interrupted" in err.lower()


def test_reaper_preserves_an_existing_error(engine):
    """A real failure reason is more useful than the generic interruption note."""
    _add(engine, "prior", IndexingStatus.EMBEDDING)
    db = sessionmaker(bind=engine)()
    repo = db.query(Repository).filter(Repository.github_name == "prior").first()
    repo.indexing_error = "rate limited by provider"
    db.commit()
    db.close()

    reap_stuck_indexing(engine)
    with engine.begin() as c:
        err = c.execute(
            text("SELECT indexing_error FROM repositories WHERE github_name = 'prior'")
        ).scalar()
    assert err == "rate limited by provider"


def test_reaper_is_idempotent(engine):
    _add(engine, "idem", IndexingStatus.CLONING)
    assert reap_stuck_indexing(engine) == 1
    assert reap_stuck_indexing(engine) == 0


def test_reaped_repo_is_retryable(engine):
    """
    The point of reaping: repos.py and seed_demo.py both self-heal only from FAILED, so
    this is what makes a stuck repository importable again.
    """
    _add(engine, "retry", IndexingStatus.PARSING)
    reap_stuck_indexing(engine)

    db = sessionmaker(bind=engine)()
    repo = db.query(Repository).filter(Repository.github_name == "retry").first()
    assert repo.status == IndexingStatus.FAILED
    db.close()
