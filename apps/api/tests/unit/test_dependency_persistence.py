"""
Dependency edges are derived once at index time and served from the database.

The behaviour that matters: graph generation no longer needs the clone on disk. It used
to read every source file inside the request, which made graph latency proportional to
repository size and silently degraded the graph once the working tree was gone.
"""

import asyncio

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.models.database import Base, CodeDependency, CodeFile, Repository
from src.services.indexing_service import IndexingService
from src.services.learning_service import LearningService


@pytest.fixture()
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _make_repo(db, clone_root):
    """A tiny TS project: app imports both helpers, one of which imports the other."""
    (clone_root / "src").mkdir(parents=True, exist_ok=True)
    (clone_root / "src" / "app.ts").write_text(
        "import { a } from './alpha';\nimport { b } from './beta';\n"
    )
    (clone_root / "src" / "alpha.ts").write_text("import { b } from './beta';\nexport const a = 1;\n")
    (clone_root / "src" / "beta.ts").write_text("export const b = 2;\n")

    repo = Repository(
        github_url="https://github.com/o/r",
        github_owner="o",
        github_name="r",
        local_path=str(clone_root),
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)

    for path in ("src/app.ts", "src/alpha.ts", "src/beta.ts"):
        db.add(CodeFile(
            repository_id=repo.id,
            path=path,
            filename=path.rsplit("/", 1)[-1],
            extension=".ts",
            language="typescript",
            imports=[],
        ))
    db.commit()
    return repo


def test_edges_are_persisted_at_index_time(db, tmp_path):
    repo = _make_repo(db, tmp_path / "clone")

    assert db.query(CodeDependency).count() == 0

    written = asyncio.run(IndexingService(db)._persist_dependency_graph(repo))

    rows = db.query(CodeDependency).filter(CodeDependency.repository_id == repo.id).all()
    assert written == len(rows)
    assert rows, "expected at least one resolved import edge"

    pairs = {(r.source_path, r.target_path) for r in rows}
    assert ("src/app.ts", "src/alpha.ts") in pairs
    assert ("src/app.ts", "src/beta.ts") in pairs
    assert ("src/alpha.ts", "src/beta.ts") in pairs

    for r in rows:
        assert r.relation
        assert r.weight >= 1
        assert 0.0 < r.confidence <= 1.0


def test_graph_survives_the_clone_being_deleted(db, tmp_path):
    """
    The point of the change. Previously, losing the working tree (redeploy, container
    restart, volume reset) silently degraded the graph to unresolved import strings.
    """
    clone = tmp_path / "clone"
    repo = _make_repo(db, clone)
    asyncio.run(IndexingService(db)._persist_dependency_graph(repo))

    persisted_pairs = {
        (r.source_path, r.target_path)
        for r in db.query(CodeDependency).filter(CodeDependency.repository_id == repo.id)
    }

    # Simulate the clone going away.
    import shutil
    shutil.rmtree(clone)
    assert not clone.exists()

    files = db.query(CodeFile).filter(CodeFile.repository_id == repo.id).all()
    file_map = {f.path: f for f in files}
    all_paths = set(file_map)

    service = LearningService(db, llm=None, vector_store=None)
    edges = service._load_or_derive_edges(repo, sorted(all_paths), all_paths, file_map)

    assert {(e.source, e.target) for e in edges} == persisted_pairs

    # And the derive-from-disk path really would have returned nothing now.
    derived = service._build_deterministic_edges(repo, sorted(all_paths), all_paths, file_map)
    assert not derived, "clone is gone, so on-demand derivation has nothing to read"


def test_falls_back_to_derivation_when_nothing_is_persisted(db, tmp_path):
    """Repositories indexed before this table existed must still produce a graph."""
    clone = tmp_path / "clone"
    repo = _make_repo(db, clone)

    assert db.query(CodeDependency).count() == 0

    files = db.query(CodeFile).filter(CodeFile.repository_id == repo.id).all()
    file_map = {f.path: f for f in files}
    all_paths = set(file_map)

    service = LearningService(db, llm=None, vector_store=None)
    edges = service._load_or_derive_edges(repo, sorted(all_paths), all_paths, file_map)

    assert edges, "expected the on-demand fallback to derive edges from the clone"


def test_edges_outside_the_node_set_are_dropped(db, tmp_path):
    """
    Scope filters and the node cap can remove a node while its edges remain in the
    table; shipping those would give the client an edge to a node it never received.
    """
    repo = _make_repo(db, tmp_path / "clone")
    asyncio.run(IndexingService(db)._persist_dependency_graph(repo))

    files = db.query(CodeFile).filter(CodeFile.repository_id == repo.id).all()
    file_map = {f.path: f for f in files if f.path != "src/beta.ts"}
    all_paths = set(file_map)

    service = LearningService(db, llm=None, vector_store=None)
    edges = service._load_or_derive_edges(repo, sorted(all_paths), all_paths, file_map)

    endpoints = {e.source for e in edges} | {e.target for e in edges}
    assert "src/beta.ts" not in endpoints
    assert endpoints <= all_paths


def test_reindex_clears_stale_edges(db, tmp_path):
    """Re-indexing must not union old and new graphs."""
    repo = _make_repo(db, tmp_path / "clone")
    asyncio.run(IndexingService(db)._persist_dependency_graph(repo))
    before = db.query(CodeDependency).filter(CodeDependency.repository_id == repo.id).count()
    assert before > 0

    # A stale edge to a file that no longer exists.
    db.add(CodeDependency(
        repository_id=repo.id,
        source_path="src/deleted.ts",
        target_path="src/beta.ts",
        relation="imports",
    ))
    db.commit()

    asyncio.run(IndexingService(db)._reset_repository_index_data(repo.id))
    assert db.query(CodeDependency).filter(CodeDependency.repository_id == repo.id).count() == 0


def test_deleting_a_repository_cascades_to_its_edges(db, tmp_path):
    repo = _make_repo(db, tmp_path / "clone")
    asyncio.run(IndexingService(db)._persist_dependency_graph(repo))
    assert db.query(CodeDependency).count() > 0

    db.delete(repo)
    db.commit()

    assert db.query(CodeDependency).count() == 0, "orphaned edges would union into a re-import"
