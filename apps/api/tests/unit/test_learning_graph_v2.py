from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.models.learning import GraphEdge, GraphNode, GraphNodeMetrics, GraphStats
from src.services.learning_service import LearningService


def build_service() -> LearningService:
    return LearningService(MagicMock(), MagicMock(), MagicMock())


def test_resolve_module_path_handles_relative_and_alias(tmp_path):
    service = build_service()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    all_paths = {
        "src/app/page.tsx",
        "src/lib/api.ts",
        "src/components/Button.tsx",
    }

    resolved_relative = service._resolve_module_path(
        source_path="src/app/page.tsx",
        module_path="../lib/api",
        all_paths=all_paths,
        repo_root=repo_root,
    )
    assert resolved_relative == "src/lib/api.ts"

    resolved_alias = service._resolve_module_path(
        source_path="src/app/page.tsx",
        module_path="@/components/Button",
        all_paths=all_paths,
        repo_root=repo_root,
    )
    assert resolved_alias == "src/components/Button.tsx"


def test_build_deterministic_edges_is_stable(tmp_path):
    service = build_service()

    repo_root = tmp_path / "repo"
    (repo_root / "src").mkdir(parents=True)
    (repo_root / "src" / "a.ts").write_text('import "./b"\nimport "./c"\n', encoding="utf-8")
    (repo_root / "src" / "b.ts").write_text('export const b = 1\n', encoding="utf-8")
    (repo_root / "src" / "c.ts").write_text('import "./b"\n', encoding="utf-8")

    file_map = {
        "src/a.ts": SimpleNamespace(imports=[]),
        "src/b.ts": SimpleNamespace(imports=[]),
        "src/c.ts": SimpleNamespace(imports=[]),
    }
    all_paths = set(file_map.keys())
    repo = SimpleNamespace(local_path=str(repo_root))

    first = service._build_deterministic_edges(repo, sorted(all_paths), all_paths, file_map)
    second = service._build_deterministic_edges(repo, sorted(all_paths), all_paths, file_map)

    first_signature = [(e.source, e.target, e.relation) for e in first]
    second_signature = [(e.source, e.target, e.relation) for e in second]

    assert first_signature == second_signature
    assert ("src/a.ts", "src/b.ts", "imports") in first_signature
    assert ("src/a.ts", "src/c.ts", "imports") in first_signature


def test_prune_graph_filters_edges_to_kept_nodes():
    service = build_service()

    nodes = [
        GraphNode(id=f"n{i}", label=f"n{i}", type="file", description="", metrics=GraphNodeMetrics(degree=5 - i, centrality=0.5))
        for i in range(5)
    ]
    edges = [
        GraphEdge(source="n0", target="n1", label="imports", relation="imports", type="imports", weight=3, confidence=0.9),
        GraphEdge(source="n1", target="n2", label="imports", relation="imports", type="imports", weight=3, confidence=0.9),
        GraphEdge(source="n2", target="n3", label="imports", relation="imports", type="imports", weight=2, confidence=0.8),
        GraphEdge(source="n3", target="n4", label="imports", relation="imports", type="imports", weight=1, confidence=0.7),
    ]

    pruned_nodes, pruned_edges = service._prune_graph(nodes, edges, max_nodes=3)

    kept_ids = {node.id for node in pruned_nodes}
    assert len(pruned_nodes) <= 3
    assert all(edge.source in kept_ids and edge.target in kept_ids for edge in pruned_edges)


def test_compute_graph_stats_density():
    service = build_service()

    nodes = [
        GraphNode(id="a", label="a", type="file", description="", group="src/app"),
        GraphNode(id="b", label="b", type="file", description="", group="src/app"),
        GraphNode(id="c", label="c", type="file", description="", group="src/lib"),
    ]
    edges = [
        GraphEdge(source="a", target="b", label="imports", relation="imports", type="imports"),
        GraphEdge(source="b", target="c", label="imports", relation="imports", type="imports"),
    ]

    stats = service._compute_graph_stats(nodes, edges)

    assert stats.nodes == 3
    assert stats.edges == 2
    assert stats.clusters == 2
    assert stats.density == round(2 / (3 * 2), 4)


def test_build_deterministic_edges_uses_import_fallback_when_file_missing(tmp_path):
    service = build_service()
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    repo = SimpleNamespace(local_path=str(repo_root))
    source_path = "src/main.ts"
    target_path = "src/shared/logger.ts"

    file_map = {
        source_path: SimpleNamespace(imports=["import { logger } from './shared/logger'"], line_count=10),
        target_path: SimpleNamespace(imports=[], line_count=5),
    }
    all_paths = set(file_map.keys())

    edges = service._build_deterministic_edges(repo, [source_path], all_paths, file_map)
    signatures = {(edge.source, edge.target) for edge in edges}

    assert (source_path, target_path) in signatures


def test_recommended_entry_view_thresholds():
    service = build_service()
    small = GraphStats(nodes=32, edges=60, clusters=4, density=0.02)
    dense = GraphStats(nodes=120, edges=420, clusters=8, density=0.03)

    assert service._recommended_entry_view(small) == "file"
    assert service._recommended_entry_view(dense) == "module"


def test_recommended_entry_view_prefers_file_when_cross_module_signal_is_low():
    service = build_service()
    dense = GraphStats(nodes=140, edges=500, clusters=8, density=0.03)

    view, reason = service._resolve_recommended_entry(
        dense,
        cross_module_ratio=0.01,
        cross_module_edges=9,
    )

    assert view == "file"
    assert reason == "low_cross_module_signal"


def test_module_graph_aggregation_deterministic():
    service = build_service()
    nodes = [
        GraphNode(id="src/app/page.tsx", label="page.tsx", type="page", description="", importance=5, loc=80, entity="file"),
        GraphNode(id="src/app/layout.tsx", label="layout.tsx", type="page", description="", importance=4, loc=40, entity="file"),
        GraphNode(id="src/lib/http.ts", label="http.ts", type="util", description="", importance=7, loc=120, entity="file"),
    ]
    edges = [
        GraphEdge(source="src/app/layout.tsx", target="src/app/page.tsx", label="imports", relation="imports", type="imports", weight=3, confidence=0.9),
        GraphEdge(source="src/app/page.tsx", target="src/lib/http.ts", label="imports", relation="imports", type="imports", weight=2, confidence=0.9),
        GraphEdge(source="src/app/layout.tsx", target="src/lib/http.ts", label="imports", relation="imports", type="imports", weight=1, confidence=0.7),
    ]

    first_nodes, first_edges = service._build_module_graph(nodes, edges)
    second_nodes, second_edges = service._build_module_graph(nodes, edges)

    assert [(n.id, n.member_count) for n in first_nodes] == [(n.id, n.member_count) for n in second_nodes]
    assert [(e.source, e.target, e.relation, e.aggregated_count) for e in first_edges] == [
        (e.source, e.target, e.relation, e.aggregated_count) for e in second_edges
    ]
    assert any(edge.source == "src/app" and edge.target == "src/lib" for edge in first_edges)
    app_node = next(node for node in first_nodes if node.id == "src/app")
    assert app_node.internal_edge_count == 3
    assert app_node.external_edge_count == 3
    assert app_node.internal_density is not None and app_node.internal_density > 0


def test_module_key_for_path_groups_scripts_and_root_files():
    service = build_service()
    assert service._module_key_for_path("scripts/create-plan.ts") == "scripts"
    assert service._module_key_for_path("scripts/utils/index.ts") == "scripts"
    assert service._module_key_for_path("package.json") == "root"
    assert service._module_key_for_path("apps/openpage-api/app/community/route.ts") == "apps/openpage-api"


def test_scope_subgraph_includes_boundary_neighbors():
    service = build_service()
    nodes = [
        GraphNode(id="src/app/page.tsx", label="page.tsx", type="page", description="", entity="file"),
        GraphNode(id="src/app/layout.tsx", label="layout.tsx", type="page", description="", entity="file"),
        GraphNode(id="src/lib/http.ts", label="http.ts", type="util", description="", entity="file"),
    ]
    edges = [
        GraphEdge(source="src/app/page.tsx", target="src/lib/http.ts", label="imports", relation="imports", type="imports"),
        GraphEdge(source="src/app/layout.tsx", target="src/app/page.tsx", label="imports", relation="imports", type="imports"),
    ]

    scoped_nodes, scoped_edges = service._extract_scoped_file_subgraph(nodes, edges, scope="src/app", hops=1)
    scoped_ids = {node.id for node in scoped_nodes}

    assert "src/app/page.tsx" in scoped_ids
    assert "src/app/layout.tsx" in scoped_ids
    assert "src/lib/http.ts" in scoped_ids
    assert len(scoped_edges) == 2


def test_edge_ranking_and_per_node_budget():
    service = build_service()
    nodes = [
        GraphNode(id="a", label="a", type="file", description="", group="g1", metrics=GraphNodeMetrics(degree=8)),
        GraphNode(id="b", label="b", type="file", description="", group="g1", metrics=GraphNodeMetrics(degree=5)),
        GraphNode(id="c", label="c", type="file", description="", group="g2", metrics=GraphNodeMetrics(degree=4)),
        GraphNode(id="d", label="d", type="file", description="", group="g2", metrics=GraphNodeMetrics(degree=2)),
    ]
    edges = [
        GraphEdge(source="a", target="b", label="imports", relation="imports", type="imports", weight=5, confidence=0.9),
        GraphEdge(source="a", target="c", label="imports", relation="imports", type="imports", weight=4, confidence=0.8),
        GraphEdge(source="a", target="d", label="imports", relation="imports", type="imports", weight=1, confidence=0.6),
    ]

    ranked = service._rank_edges(nodes, edges)
    assert all(edge.rank is not None for edge in ranked)

    budgeted = service._apply_per_node_edge_budget(nodes, ranked, per_node_limit=1)
    assert len(budgeted) >= 1
    assert len(budgeted) <= len(ranked)
    top_edge = max(ranked, key=lambda edge: edge.rank or 0.0)
    assert any(edge.source == top_edge.source and edge.target == top_edge.target for edge in budgeted)
