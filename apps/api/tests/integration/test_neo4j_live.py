"""
Neo4j store against a REAL server.

These exist because the fake-driver unit tests cannot catch a class of bug that matters.
The original delete query used "CALL { ... } IN TRANSACTIONS", which the server rejects
when run through driver.execute_query() -- that method uses an explicit transaction, and
IN TRANSACTIONS is only legal in an implicit one. The unit test asserted
`"DETACH DELETE" in query` and passed happily, so sync_repository was broken 100% of the
time while the suite was green. A fake driver does not enforce transaction semantics, so
no amount of mocking would have found it.

Skipped unless a Neo4j is reachable, so CI and a laptop without Docker stay green:

    docker run -d -p 7688:7687 -e NEO4J_AUTH=neo4j/verifypassword neo4j:5-community
    NEO4J_TEST_URI=bolt://localhost:7688 NEO4J_TEST_PASSWORD=verifypassword pytest
"""

import os

import pytest

from src.core.graph.neo4j_store import Neo4jGraphStore

URI = os.getenv("NEO4J_TEST_URI")
USER = os.getenv("NEO4J_TEST_USER", "neo4j")
PASSWORD = os.getenv("NEO4J_TEST_PASSWORD")

pytestmark = pytest.mark.skipif(
    not (URI and PASSWORD),
    reason="set NEO4J_TEST_URI and NEO4J_TEST_PASSWORD to run the live Neo4j tests",
)


def _files(*names):
    return [
        {"path": f"src/{n}.ts", "filename": f"{n}.ts", "extension": ".ts",
         "language": "typescript", "loc": 10, "module_key": "src"}
        for n in names
    ]


def _edge(a, b):
    return {"source": f"src/{a}.ts", "target": f"src/{b}.ts",
            "relation": "imports", "weight": 1, "confidence": 0.9}


@pytest.fixture()
async def store():
    from neo4j import AsyncGraphDatabase

    driver = AsyncGraphDatabase.driver(URI, auth=(USER, PASSWORD))
    s = Neo4jGraphStore(driver)
    await s.ensure_schema()
    yield s
    for repo in ("live-A", "live-B", "live-C"):
        await s.delete_repository(repo)
    await driver.close()


@pytest.mark.asyncio
async def test_schema_is_idempotent_against_a_real_server(store):
    """IF NOT EXISTS has to actually hold, not just appear in the string."""
    await store.ensure_schema()
    await store.ensure_schema()
    assert await store.verify() is True


@pytest.mark.asyncio
async def test_sync_and_delete_execute(store):
    """
    The regression. Both of these ran valid-looking Cypher that the server refused.
    sync_repository calls delete_repository first, so the delete bug broke all ingest.
    """
    result = await store.sync_repository(
        "live-A", _files("app", "alpha", "beta"), [_edge("app", "alpha"), _edge("alpha", "beta")]
    )
    assert result == {"files": 3, "edges": 2}

    deleted = await store.delete_repository("live-A")
    assert deleted == 3
    assert await store.nodes_with_degree("live-A") == []


@pytest.mark.asyncio
async def test_degree_comes_back_correct(store):
    await store.sync_repository(
        "live-A", _files("app", "alpha", "beta"), [_edge("app", "alpha"), _edge("alpha", "beta")]
    )
    by = {n["path"]: n for n in await store.nodes_with_degree("live-A")}
    assert by["src/app.ts"]["out_degree"] == 1
    assert by["src/app.ts"]["in_degree"] == 0
    assert by["src/alpha.ts"]["in_degree"] == 1
    assert by["src/beta.ts"]["in_degree"] == 1
    assert by["src/beta.ts"]["out_degree"] == 0


@pytest.mark.asyncio
async def test_traversal_is_transitive(store):
    """The capability the SQL path cannot provide at all."""
    await store.sync_repository(
        "live-A", _files("app", "alpha", "beta"), [_edge("app", "alpha"), _edge("alpha", "beta")]
    )
    reach = {r["path"] for r in await store.reachable_from("live-A", "src/app.ts", hops=3)}
    assert reach == {"src/alpha.ts", "src/beta.ts"}, "two hops must be reachable"

    blast = {r["path"] for r in await store.blast_radius("live-A", "src/beta.ts", hops=3)}
    assert blast == {"src/alpha.ts", "src/app.ts"}, "blast radius is the reverse direction"


@pytest.mark.asyncio
async def test_shortest_path_and_direction(store):
    await store.sync_repository(
        "live-A", _files("app", "alpha", "beta"), [_edge("app", "alpha"), _edge("alpha", "beta")]
    )
    hop = await store.shortest_path("live-A", "src/app.ts", "src/beta.ts")
    assert hop["distance"] == 2
    assert hop["path_nodes"] == ["src/app.ts", "src/alpha.ts", "src/beta.ts"]

    # IMPORTS is directed, so the reverse must not resolve.
    assert await store.shortest_path("live-A", "src/beta.ts", "src/app.ts") is None


@pytest.mark.asyncio
async def test_import_cycles_are_detected(store):
    await store.sync_repository(
        "live-A", _files("cycle_a", "cycle_b"),
        [_edge("cycle_a", "cycle_b"), _edge("cycle_b", "cycle_a")],
    )
    cycles = await store.import_cycles("live-A")
    assert cycles, "a two-file mutual import is a cycle"


@pytest.mark.asyncio
async def test_resync_replaces_rather_than_unions(store):
    """
    A MERGE-only sync would leave the dropped edge behind and drift into a union of every
    commit ever indexed.
    """
    await store.sync_repository(
        "live-A", _files("app", "alpha", "beta"), [_edge("app", "alpha"), _edge("alpha", "beta")]
    )
    await store.sync_repository("live-A", _files("app", "alpha", "beta"), [_edge("app", "alpha")])
    assert len(await store.edges("live-A")) == 1


@pytest.mark.asyncio
async def test_repositories_are_isolated(store):
    """Deleting one repo must not touch another's subgraph."""
    await store.sync_repository("live-B", _files("app", "alpha"), [_edge("app", "alpha")])
    await store.sync_repository("live-C", _files("app", "alpha"), [_edge("app", "alpha")])

    await store.delete_repository("live-B")

    assert await store.nodes_with_degree("live-B") == []
    assert len(await store.nodes_with_degree("live-C")) == 2


@pytest.mark.asyncio
async def test_delete_handles_more_nodes_than_one_batch(store):
    """
    delete_repository loops in bounded batches. With a single unbatched delete this would
    pass trivially; the loop is what makes a repository larger than _DELETE_BATCH fully
    removed rather than partially.
    """
    from src.core.graph.neo4j_store import _DELETE_BATCH

    names = [f"f{i}" for i in range(_DELETE_BATCH + 25)]
    await store.sync_repository("live-A", _files(*names), [])

    deleted = await store.delete_repository("live-A")
    assert deleted == len(names)
    assert await store.nodes_with_degree("live-A") == []
