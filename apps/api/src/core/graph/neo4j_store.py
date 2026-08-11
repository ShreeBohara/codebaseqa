"""
Neo4j read model for the repository dependency graph.

WHY THIS EXISTS
The graph questions that matter for understanding a codebase are traversals:
"what breaks if I change this file", "how does auth reach the database", "are there
import cycles". Those are transitive, and the Python implementation cannot answer them
-- hops is hard-capped at 2 in the API because each hop rescans the entire edge list, so
depth is quadratic in Python and a single variable-length pattern in Cypher.

WHAT IT DOES NOT DO
This is a read model, not a source of truth. code_dependencies (SQL) remains
authoritative; this is projected from it at index time and can be rebuilt at any point
by re-indexing. Every read falls back to the SQL path when Neo4j is unavailable, so
enabling this cannot take the graph endpoint down.

Degree and centrality come from COUNT {} subqueries rather than Graph Data Science
deliberately: the in-database GDS plugin is AuraDB Professional and above, and Aura
Graph Analytics sessions are an offline batch shape (2GB, one concurrent session,
30-minute TTL) that does not fit a synchronous request.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Sequence

logger = logging.getLogger(__name__)

# Applied once at startup. MERGE on (repo_id, path) is the hot write pattern, so the
# uniqueness constraints are also the indexes that make it fast -- without them every
# MERGE degrades to a label scan.
SCHEMA_STATEMENTS: Sequence[str] = (
    "CREATE CONSTRAINT file_unique IF NOT EXISTS "
    "FOR (f:File) REQUIRE (f.repo_id, f.path) IS UNIQUE",
    "CREATE CONSTRAINT module_unique IF NOT EXISTS "
    "FOR (m:Module) REQUIRE (m.repo_id, m.key) IS UNIQUE",
    "CREATE INDEX file_repo IF NOT EXISTS FOR (f:File) ON (f.repo_id)",
    "CREATE INDEX file_module IF NOT EXISTS FOR (f:File) ON (f.repo_id, f.module_key)",
)

# Batched so a large repository does not build one enormous transaction.
_INGEST_BATCH = 500

# Nodes removed per delete transaction.
_DELETE_BATCH = 1000

_MERGE_FILES = """
UNWIND $rows AS row
MERGE (f:File {repo_id: $repo_id, path: row.path})
SET f.filename    = row.filename,
    f.extension   = row.extension,
    f.language    = row.language,
    f.loc         = row.loc,
    f.module_key  = row.module_key
"""

_MERGE_EDGES = """
UNWIND $rows AS row
MATCH (s:File {repo_id: $repo_id, path: row.source})
MATCH (t:File {repo_id: $repo_id, path: row.target})
MERGE (s)-[r:IMPORTS {relation: row.relation}]->(t)
SET r.weight = row.weight, r.confidence = row.confidence
"""

# COUNT {} rather than GDS degreeCentrality -- see the module docstring.
_READ_NODES_WITH_DEGREE = """
MATCH (f:File {repo_id: $repo_id})
RETURN f.path AS path,
       f.language AS language,
       f.loc AS loc,
       f.module_key AS module_key,
       COUNT { (f)-[:IMPORTS]->(:File) } AS out_degree,
       COUNT { (f)<-[:IMPORTS]-(:File) } AS in_degree
"""

_READ_EDGES = """
MATCH (s:File {repo_id: $repo_id})-[r:IMPORTS]->(t:File {repo_id: $repo_id})
RETURN s.path AS source, t.path AS target, r.relation AS relation,
       r.weight AS weight, r.confidence AS confidence
"""

# The capability the Python path structurally cannot provide: arbitrary-depth
# traversal. $hops is interpolated rather than parameterised because Cypher does not
# allow a parameter inside a variable-length pattern bound; it is coerced to a bounded
# int by the caller before it reaches here.
_REACHABILITY = """
MATCH path = (s:File {repo_id: $repo_id, path: $path})-[:IMPORTS*1..%(hops)d]->(t:File)
RETURN DISTINCT t.path AS path, length(path) AS distance
ORDER BY distance, path
"""

_BLAST_RADIUS = """
MATCH path = (s:File {repo_id: $repo_id, path: $path})<-[:IMPORTS*1..%(hops)d]-(t:File)
RETURN DISTINCT t.path AS path, length(path) AS distance
ORDER BY distance, path
"""

_SHORTEST_PATH = """
MATCH (a:File {repo_id: $repo_id, path: $from_path}),
      (b:File {repo_id: $repo_id, path: $to_path}),
      p = shortestPath((a)-[:IMPORTS*..%(max_hops)d]->(b))
RETURN [n IN nodes(p) | n.path] AS path_nodes, length(p) AS distance
"""

# Import cycles: a real code-health signal the SQL path cannot express at all.
_CYCLES = """
MATCH (f:File {repo_id: $repo_id})
MATCH p = (f)-[:IMPORTS*2..%(max_len)d]->(f)
RETURN [n IN nodes(p) | n.path] AS cycle, length(p) AS size
ORDER BY size, cycle
LIMIT $limit
"""

# Batched with LIMIT rather than "CALL { ... } IN TRANSACTIONS", which the server
# rejects outright: driver.execute_query() runs inside an explicit transaction, and
# IN TRANSACTIONS is only legal in an implicit one
# (Neo.DatabaseError.Transaction.TransactionStartFailed). Looping bounded deletes keeps
# each transaction small without needing implicit-transaction semantics, and avoids the
# CALL (n) {...} scoped-variable syntax, which only exists from Neo4j 5.23.
_DELETE_REPO_BATCH = """
MATCH (n {repo_id: $repo_id})
WITH n LIMIT $batch
DETACH DELETE n
RETURN count(n) AS deleted
"""


class Neo4jGraphStore:
    """
    Thin async wrapper around the Neo4j driver.

    Holds no state beyond the driver, so it is safe to construct per request; the driver
    itself is a long-lived singleton (see dependencies.get_graph_driver) because it owns
    the connection pool.
    """

    def __init__(self, driver, database: Optional[str] = None):
        self._driver = driver
        self._database = database

    async def _run(self, query: str, **params) -> List[Dict[str, Any]]:
        records, _, _ = await self._driver.execute_query(
            query, database_=self._database, **params
        )
        return [dict(r) for r in records]

    # --- lifecycle ---------------------------------------------------------------

    async def verify(self) -> bool:
        """True when the server is reachable and authenticated."""
        try:
            await self._driver.verify_connectivity()
            return True
        except Exception as exc:
            logger.warning("Neo4j connectivity check failed: %s", exc)
            return False

    async def ensure_schema(self) -> None:
        """Idempotent; every statement is IF NOT EXISTS."""
        for statement in SCHEMA_STATEMENTS:
            await self._run(statement)

    # --- ingest ------------------------------------------------------------------

    async def sync_repository(
        self,
        repo_id: str,
        files: Sequence[Dict[str, Any]],
        edges: Sequence[Dict[str, Any]],
    ) -> Dict[str, int]:
        """
        Project a repository's files and edges into the graph.

        Replaces rather than merges: the previous subgraph is deleted first, because a
        MERGE-only sync would leave edges for files that no longer exist and silently
        accumulate a graph that no commit ever had.
        """
        await self.delete_repository(repo_id)

        for start in range(0, len(files), _INGEST_BATCH):
            await self._run(
                _MERGE_FILES, repo_id=repo_id, rows=list(files[start:start + _INGEST_BATCH])
            )
        for start in range(0, len(edges), _INGEST_BATCH):
            await self._run(
                _MERGE_EDGES, repo_id=repo_id, rows=list(edges[start:start + _INGEST_BATCH])
            )

        logger.info(
            "Synced %d files and %d edges into Neo4j for repo %s",
            len(files), len(edges), repo_id,
        )
        return {"files": len(files), "edges": len(edges)}

    async def delete_repository(self, repo_id: str) -> int:
        """
        Remove a repository's subgraph, in bounded batches.

        Returns the number of nodes deleted. Loops because each call deletes at most
        _DELETE_BATCH nodes; a repository with more than that would otherwise be only
        partially removed, which on the re-sync path would silently leave stale edges.
        """
        total = 0
        while True:
            rows = await self._run(
                _DELETE_REPO_BATCH, repo_id=repo_id, batch=_DELETE_BATCH
            )
            deleted = (rows[0].get("deleted") if rows else 0) or 0
            total += deleted
            if deleted < _DELETE_BATCH:
                break
        return total

    # --- reads -------------------------------------------------------------------

    async def nodes_with_degree(self, repo_id: str) -> List[Dict[str, Any]]:
        return await self._run(_READ_NODES_WITH_DEGREE, repo_id=repo_id)

    async def edges(self, repo_id: str) -> List[Dict[str, Any]]:
        return await self._run(_READ_EDGES, repo_id=repo_id)

    # --- traversals the SQL path cannot answer -----------------------------------

    @staticmethod
    def _bounded(value: int, lo: int, hi: int) -> int:
        return max(lo, min(hi, int(value)))

    async def reachable_from(self, repo_id: str, path: str, hops: int = 3) -> List[Dict[str, Any]]:
        """What this file transitively imports."""
        q = _REACHABILITY % {"hops": self._bounded(hops, 1, 10)}
        return await self._run(q, repo_id=repo_id, path=path)

    async def blast_radius(self, repo_id: str, path: str, hops: int = 3) -> List[Dict[str, Any]]:
        """What transitively imports this file -- i.e. what a change here can affect."""
        q = _BLAST_RADIUS % {"hops": self._bounded(hops, 1, 10)}
        return await self._run(q, repo_id=repo_id, path=path)

    async def shortest_path(
        self, repo_id: str, from_path: str, to_path: str, max_hops: int = 10
    ) -> Optional[Dict[str, Any]]:
        q = _SHORTEST_PATH % {"max_hops": self._bounded(max_hops, 1, 15)}
        rows = await self._run(q, repo_id=repo_id, from_path=from_path, to_path=to_path)
        return rows[0] if rows else None

    async def import_cycles(
        self, repo_id: str, max_length: int = 6, limit: int = 20
    ) -> List[Dict[str, Any]]:
        q = _CYCLES % {"max_len": self._bounded(max_length, 2, 10)}
        return await self._run(q, repo_id=repo_id, limit=max(1, int(limit)))
