"""
Neo4j graph store wiring.

IMPORTANT LIMITATION, stated rather than implied: these tests use a fake driver, so they
verify the *queries we send* and the *fallback behaviour*, not that the Cypher returns
correct results. Nothing here has executed against a Neo4j server. To validate the
Cypher itself, run `docker compose up neo4j`, set NEO4J_ENABLED=true, re-index a repo,
and check the graph endpoint against the SQL path.

What these tests do lock down is the part most likely to break silently: that the store
is off by default, that every failure path degrades to SQL rather than erroring, and
that a repository's subgraph is actually replaced (not merged) on re-sync.
"""

import pytest

from src.config import Settings
from src.core.graph.neo4j_store import SCHEMA_STATEMENTS, Neo4jGraphStore


class FakeDriver:
    """Records queries instead of executing them."""

    def __init__(self, rows=None, fail_on=None, connectivity=True):
        self.calls = []
        self._rows = rows or []
        self._fail_on = fail_on
        self._connectivity = connectivity

    async def execute_query(self, query, database_=None, **params):
        self.calls.append({"query": query, "database": database_, "params": params})
        if self._fail_on and self._fail_on in query:
            raise RuntimeError("simulated neo4j failure")
        return self._rows, None, None

    async def verify_connectivity(self):
        if not self._connectivity:
            raise RuntimeError("unreachable")

    async def close(self):
        self.calls.append({"query": "__closed__"})


def _queries(driver):
    return " || ".join(c["query"] for c in driver.calls)


# --- disabled by default ---------------------------------------------------------

def test_graph_store_is_disabled_by_default():
    """A new datastore must not become load-bearing by accident."""
    assert Settings(_env_file=None).neo4j_enabled is False


def test_get_graph_store_returns_none_when_disabled(monkeypatch):
    import src.dependencies as deps
    monkeypatch.setattr(deps, "settings", Settings(_env_file=None, neo4j_enabled=False))
    deps.get_graph_driver.cache_clear()
    assert deps.get_graph_store() is None


def test_get_graph_store_returns_none_when_password_missing(monkeypatch):
    """Enabled but unconfigured must degrade, not raise at import time."""
    import src.dependencies as deps
    monkeypatch.setattr(
        deps, "settings",
        Settings(_env_file=None, neo4j_enabled=True, neo4j_password=None),
    )
    deps.get_graph_driver.cache_clear()
    assert deps.get_graph_store() is None
    deps.get_graph_driver.cache_clear()


# --- schema ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ensure_schema_is_idempotent_by_construction():
    driver = FakeDriver()
    await Neo4jGraphStore(driver).ensure_schema()

    assert len(driver.calls) == len(SCHEMA_STATEMENTS)
    # Re-running must be safe, which means every statement carries IF NOT EXISTS.
    for statement in SCHEMA_STATEMENTS:
        assert "IF NOT EXISTS" in statement


@pytest.mark.asyncio
async def test_schema_constrains_uniqueness_per_repo():
    """(repo_id, path) must be unique, or re-sync would duplicate every file node."""
    joined = " ".join(SCHEMA_STATEMENTS)
    assert "f.repo_id, f.path) IS UNIQUE" in joined
    assert "m.repo_id, m.key) IS UNIQUE" in joined


# --- ingest ----------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sync_replaces_rather_than_merges():
    """
    A MERGE-only sync leaves edges for deleted files behind, so the graph drifts into a
    union of every commit ever indexed. Sync must delete the subgraph first.
    """
    driver = FakeDriver()
    store = Neo4jGraphStore(driver)
    await store.sync_repository(
        "repo-1",
        files=[{"path": "a.ts", "filename": "a.ts", "extension": ".ts",
                "language": "typescript", "loc": 10, "module_key": "root"}],
        edges=[{"source": "a.ts", "target": "b.ts", "relation": "imports",
                "weight": 1, "confidence": 0.9}],
    )
    assert "DETACH DELETE" in driver.calls[0]["query"]
    assert "MERGE (f:File" in _queries(driver)
    assert "MERGE (s)-[r:IMPORTS" in _queries(driver)


@pytest.mark.asyncio
async def test_sync_batches_large_repositories():
    """One transaction per 500 rows, not one transaction for the whole repo."""
    driver = FakeDriver()
    files = [
        {"path": f"f{i}.ts", "filename": f"f{i}.ts", "extension": ".ts",
         "language": "typescript", "loc": 1, "module_key": "root"}
        for i in range(1200)
    ]
    await Neo4jGraphStore(driver).sync_repository("r", files=files, edges=[])
    merge_calls = [c for c in driver.calls if "MERGE (f:File" in c["query"]]
    assert len(merge_calls) == 3  # 500 + 500 + 200
    assert sum(len(c["params"]["rows"]) for c in merge_calls) == 1200


@pytest.mark.asyncio
async def test_edges_are_scoped_to_the_repository():
    """Both endpoints are matched with repo_id, so edges cannot cross repositories."""
    driver = FakeDriver()
    await Neo4jGraphStore(driver).sync_repository(
        "r", files=[], edges=[{"source": "a", "target": "b", "relation": "imports",
                               "weight": 1, "confidence": 0.5}])
    edge_q = [c["query"] for c in driver.calls if "IMPORTS" in c["query"]][0]
    assert edge_q.count("repo_id: $repo_id") == 2


# --- reads use COUNT{} rather than GDS -------------------------------------------

@pytest.mark.asyncio
async def test_degree_uses_count_subqueries_not_gds():
    """
    GDS is deliberately avoided: the in-database plugin is AuraDB Professional+ and
    Aura Graph Analytics sessions are an offline batch shape.
    """
    driver = FakeDriver(rows=[{"path": "a.ts", "in_degree": 1, "out_degree": 2}])
    await Neo4jGraphStore(driver).nodes_with_degree("r")
    q = driver.calls[0]["query"]
    assert "COUNT {" in q
    assert "gds." not in q.lower()


# --- traversals ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_traversal_depth_is_bounded():
    """An unbounded variable-length pattern is a trivial way to hang the server."""
    driver = FakeDriver()
    store = Neo4jGraphStore(driver)

    await store.reachable_from("r", "a.ts", hops=999)
    assert "IMPORTS*1..10]" in driver.calls[-1]["query"]

    await store.blast_radius("r", "a.ts", hops=0)
    assert "IMPORTS*1..1]" in driver.calls[-1]["query"]


@pytest.mark.asyncio
async def test_blast_radius_traverses_inbound_edges():
    """"What breaks if I change this" is the reverse direction of "what this imports"."""
    driver = FakeDriver()
    store = Neo4jGraphStore(driver)
    await store.reachable_from("r", "a.ts", hops=2)
    forward = driver.calls[-1]["query"]
    await store.blast_radius("r", "a.ts", hops=2)
    reverse = driver.calls[-1]["query"]
    assert "-[:IMPORTS*1..2]->" in forward
    assert "<-[:IMPORTS*1..2]-" in reverse


@pytest.mark.asyncio
async def test_shortest_path_returns_none_when_unreachable():
    store = Neo4jGraphStore(FakeDriver(rows=[]))
    assert await store.shortest_path("r", "a.ts", "z.ts") is None


@pytest.mark.asyncio
async def test_import_cycles_requires_length_at_least_two():
    """A self-loop is not an import cycle worth reporting."""
    driver = FakeDriver()
    await Neo4jGraphStore(driver).import_cycles("r", max_length=1)
    assert "IMPORTS*2..2]" in driver.calls[-1]["query"]


# --- failure degrades to SQL, never raises ---------------------------------------

@pytest.mark.asyncio
async def test_verify_returns_false_when_unreachable():
    assert await Neo4jGraphStore(FakeDriver(connectivity=False)).verify() is False


@pytest.mark.asyncio
async def test_indexing_survives_a_graph_sync_failure(monkeypatch, tmp_path):
    """
    The whole point of SQL staying authoritative: a Neo4j outage during indexing must
    not fail the index or lose the SQL edges.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from src.models.database import Base, CodeDependency, CodeFile, Repository
    from src.services.indexing_service import IndexingService

    engine = create_engine(f"sqlite:///{tmp_path / 'x.db'}")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()

    clone = tmp_path / "clone"
    (clone / "src").mkdir(parents=True)
    (clone / "src" / "a.ts").write_text("import { b } from './b';\n")
    (clone / "src" / "b.ts").write_text("export const b = 1;\n")

    repo = Repository(github_url="https://github.com/o/r", github_owner="o",
                      github_name="r", local_path=str(clone))
    db.add(repo)
    db.commit()
    db.refresh(repo)
    for path in ("src/a.ts", "src/b.ts"):
        db.add(CodeFile(repository_id=repo.id, path=path, filename=path[-4:],
                        extension=".ts", language="typescript", imports=[]))
    db.commit()

    failing = Neo4jGraphStore(FakeDriver(fail_on="DETACH DELETE"))
    monkeypatch.setattr("src.dependencies.get_graph_store", lambda: failing)

    written = await IndexingService(db)._persist_dependency_graph(repo)

    assert written > 0
    assert db.query(CodeDependency).filter(CodeDependency.repository_id == repo.id).count() > 0
    db.close()
