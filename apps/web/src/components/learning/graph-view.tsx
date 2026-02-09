'use client';

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
    Background,
    BackgroundVariant,
    Controls,
    EdgeTypes,
    MarkerType,
    MiniMap,
    Node,
    NodeTypes,
    ReactFlow,
    ReactFlowInstance,
    ReactFlowProvider,
    useEdgesState,
    useNodesState,
    type Viewport,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { toPng } from 'html-to-image';
import { AnimatePresence, motion } from 'framer-motion';
import { ArrowLeft, Eye, EyeOff, Loader2, Search, Sparkles, X } from 'lucide-react';
import { api, DependencyGraph } from '@/lib/api-client';

import { CustomEdge, CustomFlowEdge, EdgeType, EDGE_TYPES } from './graph/CustomEdge';
import { CustomFlowNode, CustomNode, CustomNodeData, FILE_TYPES, FileType, detectFileType } from './graph/CustomNode';
import { GraphLegend } from './graph/GraphLegend';
import { NodeDetailPanel } from './graph/NodeDetailPanel';
import { GraphToolbar } from './graph/GraphToolbar';
import { applyAutoLayout } from './graph/graph-layouts';

interface GraphViewProps {
    repoId: string;
    repoName?: string;
}

type GraphGranularity = 'auto' | 'module' | 'file';
type GraphViewMode = 'module' | 'file';

interface GraphRequestState {
    granularity: GraphGranularity;
    scope?: string;
    focusNode?: string;
    hops: 1 | 2;
}

interface GraphLoadOptions extends Partial<GraphRequestState> {
    force?: boolean;
}

const nodeTypes = {
    custom: CustomNode,
} as unknown as NodeTypes;

const edgeTypes = {
    custom: CustomEdge,
} as unknown as EdgeTypes;

const ALL_FILE_TYPES = Object.keys(FILE_TYPES) as FileType[];
const LOW_ZOOM_EDGE_BUDGET = 60;
const MID_ZOOM_EDGE_BUDGET = 180;
const DENSE_MODE_V21_ENABLED = process.env.NEXT_PUBLIC_GRAPH_DENSE_MODE_V21 !== 'false';

function edgeRankSort(a: CustomFlowEdge, b: CustomFlowEdge): number {
    const aRank = (a.data?.rank as number | undefined) || 0;
    const bRank = (b.data?.rank as number | undefined) || 0;
    if (bRank !== aRank) return bRank - aRank;
    const aWeight = (a.data?.weight as number | undefined) || 0;
    const bWeight = (b.data?.weight as number | undefined) || 0;
    if (bWeight !== aWeight) return bWeight - aWeight;
    return a.id.localeCompare(b.id);
}

function budgetForZoom(zoom: number): number {
    if (zoom < 0.55) return LOW_ZOOM_EDGE_BUDGET;
    if (zoom < 0.9) return MID_ZOOM_EDGE_BUDGET;
    return Number.POSITIVE_INFINITY;
}

export function GraphView({ repoId }: GraphViewProps) {
    const [nodes, setNodes, onNodesChange] = useNodesState<CustomFlowNode>([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState<CustomFlowEdge>([]);

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedNode, setSelectedNode] = useState<string | null>(null);
    const [isExporting, setIsExporting] = useState(false);
    const [showMiniMap, setShowMiniMap] = useState(true);
    const [inspectorOpen, setInspectorOpen] = useState(true);
    const [graphMeta, setGraphMeta] = useState<DependencyGraph['meta'] | null>(null);
    const [currentView, setCurrentView] = useState<GraphViewMode>('file');
    const [currentScope, setCurrentScope] = useState<string | null>(null);
    const [recommendedEntry, setRecommendedEntry] = useState<GraphViewMode | null>(null);

    const [activeTypes, setActiveTypes] = useState<Set<FileType>>(() => new Set(ALL_FILE_TYPES));
    const [flowInstance, setFlowInstance] = useState<ReactFlowInstance<CustomFlowNode, CustomFlowEdge> | null>(null);
    const [zoomLevel, setZoomLevel] = useState(1);

    const [focusMode, setFocusMode] = useState(false);
    const [focusHops, setFocusHops] = useState<1 | 2>(1);
    const [focusedNodeId, setFocusedNodeId] = useState<string | null>(null);
    const [headerHeight, setHeaderHeight] = useState(120);

    const isFetchingRef = useRef(false);
    const graphViewRecordedRef = useRef(false);
    const viewedNodeIdsRef = useRef<Set<string>>(new Set());
    const requestRef = useRef<GraphRequestState>({
        granularity: 'file',
        hops: 1,
    });
    const containerRef = useRef<HTMLDivElement>(null);
    const headerRef = useRef<HTMLDivElement>(null);

    const resetFocusState = useCallback(() => {
        setFocusMode(false);
        setFocusHops(1);
        setFocusedNodeId(null);
    }, []);

    const loadGraph = useCallback(async (options: GraphLoadOptions = {}) => {
        const nextRequest: GraphRequestState = {
            ...requestRef.current,
            ...options,
            granularity: options.granularity || requestRef.current.granularity,
            scope: options.scope !== undefined ? options.scope : requestRef.current.scope,
            focusNode: options.focusNode !== undefined ? options.focusNode : requestRef.current.focusNode,
            hops: (options.hops || requestRef.current.hops || 1) as 1 | 2,
        };
        requestRef.current = nextRequest;

        if (isFetchingRef.current && !options.force) {
            return;
        }

        isFetchingRef.current = true;
        setLoading(true);
        setError(null);

        try {
            const data: DependencyGraph = await api.getDependencyGraph(repoId, {
                granularity: nextRequest.granularity,
                scope: nextRequest.scope,
                focusNode: nextRequest.focusNode,
                hops: nextRequest.hops,
            });

            if (!data.nodes || data.nodes.length === 0) {
                setNodes([]);
                setEdges([]);
                setGraphMeta(data.meta || null);
                setSelectedNode(null);
                setFocusedNodeId(null);
                setCurrentScope(null);
                setCurrentView('file');
                return;
            }

            const initialNodes: CustomFlowNode[] = data.nodes.map((node) => {
                const normalizedType = node.type as keyof typeof FILE_TYPES;
                const fileType = normalizedType in FILE_TYPES ? (normalizedType as FileType) : detectFileType(node.id);

                return {
                    id: node.id,
                    type: 'custom',
                    data: {
                        label: node.label || node.id.split('/').pop() || node.id,
                        description: node.description,
                        filePath: node.id,
                        fileType,
                        entity: node.entity || 'file',
                        moduleKey: node.module_key,
                        importance: node.importance,
                        linesOfCode: node.loc_total || node.loc,
                        group: node.group,
                        exports: node.exports,
                        metrics: node.metrics,
                        memberCount: node.member_count,
                        topFiles: node.top_files,
                        dominantTypes: node.dominant_types,
                        internalEdgeCount: node.internal_edge_count,
                        externalEdgeCount: node.external_edge_count,
                        internalDensity: node.internal_density,
                    },
                    position: { x: 0, y: 0 },
                };
            });

            const nodeIds = new Set(initialNodes.map((node) => node.id));
            const initialEdges: CustomFlowEdge[] = (data.edges || [])
                .filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target))
                .map((edge) => {
                    const maybeType = (edge.relation || edge.type || 'imports') as EdgeType;
                    const edgeType = maybeType in EDGE_TYPES ? maybeType : 'imports';
                    const relation = edge.relation || edge.type || 'imports';
                    return {
                        id: `${edge.source}-${edge.target}-${relation}`,
                        source: edge.source,
                        target: edge.target,
                        type: 'custom',
                        data: {
                            label: edge.label || relation,
                            relation,
                            type: edgeType,
                            weight: edge.weight,
                            confidence: edge.confidence,
                            rank: edge.rank,
                        },
                    };
                });

            const layoutedNodes = await applyAutoLayout(initialNodes, initialEdges);
            setNodes(layoutedNodes);
            setEdges(initialEdges);
            setGraphMeta(data.meta || null);
            setSelectedNode(null);
            setFocusedNodeId(null);
            setCurrentView((data.meta?.view as GraphViewMode | undefined) || 'file');
            setCurrentScope(data.meta?.scope || null);
            setRecommendedEntry((data.meta?.recommended_entry as GraphViewMode | undefined) || null);

            setTimeout(() => {
                flowInstance?.fitView({ padding: 0.16, duration: 350 });
            }, 20);
        } catch (requestError) {
            console.error('Failed to load graph:', requestError);
            setNodes([]);
            setEdges([]);
            setGraphMeta(null);
            setError('Failed to generate graph. Please try regenerate.');
        } finally {
            setLoading(false);
            isFetchingRef.current = false;
        }
    }, [flowInstance, repoId, setEdges, setNodes]);

    useEffect(() => {
        graphViewRecordedRef.current = false;
        viewedNodeIdsRef.current.clear();
        requestRef.current = {
            granularity: 'file',
            hops: 1,
        };
        resetFocusState();
        void loadGraph({ force: true, granularity: requestRef.current.granularity, hops: 1 });
    }, [loadGraph, repoId, resetFocusState]);

    useEffect(() => {
        if (!loading && nodes.length > 0 && !graphViewRecordedRef.current) {
            graphViewRecordedRef.current = true;
            void api.recordGraphView(repoId).catch(() => null);
        }
    }, [loading, nodes.length, repoId]);

    const typeCounts = useMemo(() => {
        const counts: Partial<Record<FileType, number>> = {};
        nodes.forEach((node) => {
            const type = (node.data.fileType || 'default') as FileType;
            counts[type] = (counts[type] || 0) + 1;
        });
        return counts;
    }, [nodes]);

    const normalizedSearch = searchQuery.trim().toLowerCase();

    const filteredNodes = useMemo(() => {
        return nodes.filter((node) => {
            const type = (node.data.fileType || 'default') as FileType;
            if (!activeTypes.has(type)) {
                return false;
            }
            if (!normalizedSearch) {
                return true;
            }
            return (
                node.data.label.toLowerCase().includes(normalizedSearch) ||
                node.data.filePath.toLowerCase().includes(normalizedSearch)
            );
        });
    }, [activeTypes, nodes, normalizedSearch]);

    const filteredNodeIds = useMemo(() => new Set(filteredNodes.map((node) => node.id)), [filteredNodes]);

    const filteredEdges = useMemo(() => {
        return edges
            .filter((edge) => filteredNodeIds.has(edge.source) && filteredNodeIds.has(edge.target))
            .sort(edgeRankSort);
    }, [edges, filteredNodeIds]);

    useEffect(() => {
        if (selectedNode && !filteredNodeIds.has(selectedNode)) {
            setSelectedNode(null);
        }
        if (focusedNodeId && !filteredNodeIds.has(focusedNodeId)) {
            setFocusedNodeId(null);
        }
    }, [filteredNodeIds, focusedNodeId, selectedNode]);

    const focusSeedNode = focusMode ? (focusedNodeId || selectedNode) : null;
    const focusNeighborhoodNodeIds = useMemo(() => {
        if (!focusSeedNode) {
            return null;
        }
        const set = new Set<string>([focusSeedNode]);
        for (let hop = 0; hop < focusHops; hop += 1) {
            const additions = new Set<string>();
            filteredEdges.forEach((edge) => {
                if (set.has(edge.source)) additions.add(edge.target);
                if (set.has(edge.target)) additions.add(edge.source);
            });
            additions.forEach((id) => set.add(id));
        }
        return set;
    }, [filteredEdges, focusHops, focusSeedNode]);

    const selectedNeighborhoodNodeIds = useMemo(() => {
        if (!selectedNode) return new Set<string>();
        const set = new Set<string>([selectedNode]);
        filteredEdges.forEach((edge) => {
            if (edge.source === selectedNode) set.add(edge.target);
            if (edge.target === selectedNode) set.add(edge.source);
        });
        return set;
    }, [filteredEdges, selectedNode]);

    const selectedNeighborhoodEdgeIds = useMemo(() => {
        if (!selectedNode) return new Set<string>();
        return new Set(
            filteredEdges
                .filter((edge) => edge.source === selectedNode || edge.target === selectedNode)
                .map((edge) => edge.id)
        );
    }, [filteredEdges, selectedNode]);

    const hideNonFocusNodes = Boolean(focusMode && focusNeighborhoodNodeIds && zoomLevel < 0.7);
    const visibleNodeIds = useMemo(() => {
        if (!hideNonFocusNodes || !focusNeighborhoodNodeIds) {
            return filteredNodeIds;
        }
        return new Set<string>(
            [...focusNeighborhoodNodeIds, ...selectedNeighborhoodNodeIds].filter((id) => filteredNodeIds.has(id))
        );
    }, [filteredNodeIds, focusNeighborhoodNodeIds, hideNonFocusNodes, selectedNeighborhoodNodeIds]);

    const edgeBudget = budgetForZoom(zoomLevel);
    const budgetedEdgeIds = useMemo(() => {
        if (!Number.isFinite(edgeBudget)) {
            return new Set(filteredEdges.map((edge) => edge.id));
        }

        const top = filteredEdges.slice(0, edgeBudget).map((edge) => edge.id);
        const keep = new Set(top);

        if (selectedNode) {
            filteredEdges.forEach((edge) => {
                if (edge.source === selectedNode || edge.target === selectedNode) {
                    keep.add(edge.id);
                }
            });
        }

        if (focusNeighborhoodNodeIds) {
            filteredEdges.forEach((edge) => {
                if (focusNeighborhoodNodeIds.has(edge.source) && focusNeighborhoodNodeIds.has(edge.target)) {
                    keep.add(edge.id);
                }
            });
        }
        return keep;
    }, [edgeBudget, filteredEdges, focusNeighborhoodNodeIds, selectedNode]);

    const renderedNodes = useMemo(
        () =>
            filteredNodes.map((node) => {
                const isInFocusNeighborhood = focusNeighborhoodNodeIds?.has(node.id) ?? false;
                const inSelectedNeighborhood = selectedNeighborhoodNodeIds.has(node.id);
                const shouldHide = !visibleNodeIds.has(node.id) && !inSelectedNeighborhood;
                return {
                    ...node,
                    hidden: shouldHide,
                    data: {
                        ...node.data,
                        lod: zoomLevel < 0.7 ? ('compact' as const) : ('full' as const),
                        isHighlighted: selectedNeighborhoodNodeIds.has(node.id) || isInFocusNeighborhood,
                    },
                };
            }),
        [filteredNodes, focusNeighborhoodNodeIds, selectedNeighborhoodNodeIds, visibleNodeIds, zoomLevel]
    );

    const renderedEdges = useMemo(
        () =>
            filteredEdges.map((edge) => {
                const visibleByBudget = budgetedEdgeIds.has(edge.id);
                const visibleByNode = visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target);
                const inFocusNeighborhood = focusNeighborhoodNodeIds
                    ? focusNeighborhoodNodeIds.has(edge.source) && focusNeighborhoodNodeIds.has(edge.target)
                    : true;
                const inSelectedNeighborhood = selectedNeighborhoodEdgeIds.has(edge.id);
                const keepBySelection = inSelectedNeighborhood && visibleByNode;
                const keepByBudgetAndFocus = visibleByBudget && visibleByNode && (inFocusNeighborhood || !focusMode);
                const hidden = !(keepBySelection || keepByBudgetAndFocus);
                return {
                    ...edge,
                    hidden,
                    data: {
                        ...edge.data,
                        zoomLevel,
                        isDimmed: focusMode && !inFocusNeighborhood && !inSelectedNeighborhood,
                        isHighlighted:
                            !!selectedNode && (edge.source === selectedNode || edge.target === selectedNode),
                    },
                };
            }),
        [
            budgetedEdgeIds,
            filteredEdges,
            focusMode,
            focusNeighborhoodNodeIds,
            selectedNeighborhoodEdgeIds,
            selectedNode,
            visibleNodeIds,
            zoomLevel,
        ]
    );

    const selectedNodeData = useMemo(
        () => (selectedNode ? nodes.find((node) => node.id === selectedNode) || null : null),
        [nodes, selectedNode]
    );

    const incomingEdges = selectedNode
        ? edges
              .filter((edge) => edge.target === selectedNode)
              .map((edge) => ({
                  source: edge.source,
                  label: typeof edge.data?.relation === 'string' ? edge.data.relation : edge.data?.label as string | undefined,
              }))
        : [];

    const outgoingEdges = selectedNode
        ? edges
              .filter((edge) => edge.source === selectedNode)
              .map((edge) => ({
                  target: edge.target,
                  label: typeof edge.data?.relation === 'string' ? edge.data.relation : edge.data?.label as string | undefined,
              }))
        : [];

    const handleSelectNode = useCallback(
        (nodeId: string) => {
            setSelectedNode(nodeId);
            if (focusMode) {
                setFocusedNodeId(nodeId);
            }
            if (!viewedNodeIdsRef.current.has(nodeId)) {
                viewedNodeIdsRef.current.add(nodeId);
                void api.recordGraphNodeViewed(repoId, nodeId).catch(() => null);
            }
        },
        [focusMode, repoId]
    );

    const handleFit = useCallback(() => {
        flowInstance?.fitView({ nodes: renderedNodes.filter((node) => !node.hidden), padding: 0.18, duration: 280 });
    }, [flowInstance, renderedNodes]);

    const handleCenter = useCallback(() => {
        if (!flowInstance) return;

        if (selectedNodeData) {
            flowInstance.setCenter(
                selectedNodeData.position.x + 135,
                selectedNodeData.position.y + 46,
                { zoom: Math.max(0.95, zoomLevel), duration: 260 }
            );
            return;
        }

        flowInstance.fitView({ nodes: renderedNodes.filter((node) => !node.hidden), padding: 0.18, duration: 260 });
    }, [flowInstance, renderedNodes, selectedNodeData, zoomLevel]);

    const handleExport = useCallback(async () => {
        if (!containerRef.current) return;
        setIsExporting(true);
        try {
            const canvasNode = containerRef.current.querySelector('.react-flow') as HTMLElement | null;
            if (!canvasNode) return;

            const dataUrl = await toPng(canvasNode, {
                backgroundColor: '#09090b',
                quality: 1,
                pixelRatio: 2,
            });
            const link = document.createElement('a');
            link.download = `dependency-graph-${repoId}.png`;
            link.href = dataUrl;
            link.click();
        } catch (exportError) {
            console.error('Failed to export graph:', exportError);
        } finally {
            setIsExporting(false);
        }
    }, [repoId]);

    const getMinimapNodeColor = (node: Node) => {
        const nodeData = node.data as CustomNodeData | undefined;
        const fileType = (nodeData?.fileType || 'default') as FileType;
        return FILE_TYPES[fileType]?.color || FILE_TYPES.default.color;
    };

    const handleToggleType = (type: FileType) => {
        setActiveTypes((prev) => {
            const next = new Set(prev);
            if (next.has(type)) {
                next.delete(type);
            } else {
                next.add(type);
            }
            return next.size === 0 ? new Set([type]) : next;
        });
    };

    const handleDrillDownModule = useCallback((moduleKey: string) => {
        setSelectedNode(null);
        resetFocusState();
        void loadGraph({
            force: true,
            granularity: 'file',
            scope: moduleKey,
            focusNode: undefined,
            hops: 1,
        });
    }, [loadGraph, resetFocusState]);

    const handleBackToOverview = useCallback(() => {
        setSelectedNode(null);
        resetFocusState();
        void loadGraph({
            force: true,
            granularity: DENSE_MODE_V21_ENABLED ? 'module' : 'file',
            scope: undefined,
            focusNode: undefined,
            hops: 1,
        });
    }, [loadGraph, resetFocusState]);

    const handleSwitchView = useCallback((nextView: GraphViewMode) => {
        if (nextView === 'module' && !DENSE_MODE_V21_ENABLED) {
            return;
        }
        setSelectedNode(null);
        resetFocusState();
        void loadGraph({
            force: true,
            granularity: nextView,
            scope: undefined,
            focusNode: undefined,
            hops: 1,
        });
    }, [loadGraph, resetFocusState]);

    const handleRegenerate = useCallback(() => {
        resetFocusState();
        void loadGraph({ force: true, scope: requestRef.current.scope, granularity: requestRef.current.granularity });
    }, [loadGraph, resetFocusState]);

    const handleViewportChange = useCallback((_: MouseEvent | TouchEvent | null, viewport: Viewport) => {
        setZoomLevel((prev) => (Math.abs(prev - viewport.zoom) < 0.03 ? prev : viewport.zoom));
    }, []);

    useEffect(() => {
        const element = headerRef.current;
        if (!element) return;

        const update = () => {
            setHeaderHeight(element.offsetTop + element.offsetHeight + 10);
        };

        update();
        const observer = new ResizeObserver(update);
        observer.observe(element);
        window.addEventListener('resize', update);

        return () => {
            observer.disconnect();
            window.removeEventListener('resize', update);
        };
    }, []);

    const shownEdges = renderedEdges.filter((edge) => !edge.hidden).length;
    const totalVisibleScopeEdges = filteredEdges.length;

    const totalNodes = graphMeta?.stats?.nodes ?? nodes.length;
    const totalEdges = graphMeta?.stats?.edges ?? edges.length;
    const density = graphMeta?.stats?.density ?? (nodes.length > 1 ? edges.length / (nodes.length * (nodes.length - 1)) : 0);
    const crossModuleRatio = graphMeta?.cross_module_ratio;
    const internalEdgesSummarized = graphMeta?.internal_edges_summarized;

    return (
        <ReactFlowProvider>
            <div ref={containerRef} className="h-full w-full bg-zinc-950">
                <div
                    className={`grid h-full grid-cols-1 ${
                        inspectorOpen ? 'md:grid-cols-[minmax(0,1fr)_390px]' : 'md:grid-cols-[minmax(0,1fr)_52px]'
                    }`}
                >
                    <div className="relative min-h-0">
                        <motion.div
                            ref={headerRef}
                            initial={{ opacity: 0, y: -8 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="absolute left-4 right-4 top-4 z-40 flex flex-col gap-2"
                        >
                            <div className="flex flex-wrap items-center gap-2">
                                <div className="relative w-full max-w-sm">
                                    <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
                                    <input
                                        type="text"
                                        value={searchQuery}
                                        onChange={(event) => setSearchQuery(event.target.value)}
                                        placeholder="Search nodes..."
                                        className="w-full rounded-lg border border-zinc-800 bg-zinc-900/90 py-2 pl-9 pr-8 text-sm text-zinc-100 placeholder:text-zinc-500 focus:border-indigo-400/40 focus:outline-none"
                                    />
                                    {searchQuery && (
                                        <button
                                            type="button"
                                            onClick={() => setSearchQuery('')}
                                            className="absolute right-2 top-1/2 -translate-y-1/2 rounded p-1 hover:bg-zinc-800"
                                        >
                                            <X size={12} className="text-zinc-400" />
                                        </button>
                                    )}
                                </div>

                            </div>

                            <div className="hidden flex-wrap items-center gap-2 rounded-lg border border-zinc-800 bg-zinc-900/85 px-3 py-2 text-xs text-zinc-300 lg:flex">
                                <Sparkles size={12} className="text-indigo-300" />
                                <span>{totalNodes} nodes</span>
                                <span className="text-zinc-600">•</span>
                                <span>{totalEdges} edges</span>
                                <span className="text-zinc-600">•</span>
                                <span className="rounded bg-zinc-800 px-1.5 py-0.5 text-[10px] text-zinc-400">{density.toFixed(2)} density</span>
                                <span className="rounded border border-zinc-700 bg-zinc-900 px-1.5 py-0.5 text-[10px]">
                                    {currentView === 'module' ? 'Overview' : 'File Scope'}
                                </span>
                                {recommendedEntry && (
                                    <span className="rounded border border-zinc-700 bg-zinc-900 px-1.5 py-0.5 text-[10px] text-zinc-400">
                                        auto: {recommendedEntry}
                                    </span>
                                )}
                                {graphMeta?.entry_reason && (
                                    <span className="rounded border border-zinc-700 bg-zinc-900 px-1.5 py-0.5 text-[10px] text-zinc-500">
                                        {graphMeta.entry_reason}
                                    </span>
                                )}
                                <span className="rounded border border-zinc-700 bg-zinc-900 px-1.5 py-0.5 text-[10px]">
                                    Showing {shownEdges}/{totalVisibleScopeEdges} edges
                                </span>
                                {typeof crossModuleRatio === 'number' && (
                                    <span className="rounded border border-zinc-700 bg-zinc-900 px-1.5 py-0.5 text-[10px] text-zinc-300">
                                        cross {(crossModuleRatio * 100).toFixed(1)}%
                                    </span>
                                )}
                                {typeof internalEdgesSummarized === 'number' && (
                                    <span className="rounded border border-zinc-700 bg-zinc-900 px-1.5 py-0.5 text-[10px] text-zinc-300">
                                        internal {internalEdgesSummarized}
                                    </span>
                                )}
                                {graphMeta?.truncated && (
                                    <span className="rounded bg-amber-500/20 px-1.5 py-0.5 text-[10px] text-amber-300">pruned</span>
                                )}
                            </div>

                            <div className="flex flex-wrap items-center justify-between gap-2">
                                <div className="flex flex-wrap items-center gap-2">
                                    <div className="inline-flex items-center gap-1 rounded-lg border border-zinc-700 bg-zinc-900/85 p-1">
                                        <span className="px-1.5 text-[10px] font-medium uppercase tracking-wider text-zinc-500">View</span>
                                        <button
                                            type="button"
                                            onClick={() => handleSwitchView('file')}
                                            className={`rounded-md px-2.5 py-1.5 text-[11px] ${
                                                currentView === 'file'
                                                    ? 'bg-indigo-500/20 text-indigo-200'
                                                    : 'text-zinc-300 hover:bg-zinc-800'
                                            }`}
                                            title="Show file-level graph"
                                        >
                                            File Graph
                                        </button>
                                        {DENSE_MODE_V21_ENABLED && (
                                            <button
                                                type="button"
                                                onClick={() => handleSwitchView('module')}
                                                className={`rounded-md px-2.5 py-1.5 text-[11px] ${
                                                    currentView === 'module'
                                                        ? 'bg-indigo-500/20 text-indigo-200'
                                                        : 'text-zinc-300 hover:bg-zinc-800'
                                                }`}
                                                title="Show module overview"
                                            >
                                                Overview
                                            </button>
                                        )}
                                    </div>

                                    <div className="inline-flex items-center gap-1 rounded-lg border border-zinc-700 bg-zinc-900/85 p-1">
                                        <span className="px-1.5 text-[10px] font-medium uppercase tracking-wider text-zinc-500">Focus</span>
                                        <button
                                            type="button"
                                            onClick={() => {
                                                setFocusMode((prev) => {
                                                    const next = !prev;
                                                    if (next && selectedNode) {
                                                        setFocusedNodeId(selectedNode);
                                                    }
                                                    if (!next) {
                                                        setFocusedNodeId(null);
                                                    }
                                                    return next;
                                                });
                                            }}
                                            className={`inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-[11px] ${
                                                focusMode
                                                    ? 'bg-indigo-500/20 text-indigo-200'
                                                    : 'text-zinc-300 hover:bg-zinc-800'
                                            }`}
                                            title="Toggle focus neighborhood mode"
                                        >
                                            {focusMode ? <Eye size={13} /> : <EyeOff size={13} />}
                                            <span>{focusMode ? 'On' : 'Off'}</span>
                                        </button>
                                        {focusMode && (
                                            <>
                                                <div className="mx-1 h-4 w-px bg-zinc-700/70" />
                                                <button
                                                    type="button"
                                                    onClick={() => setFocusHops(1)}
                                                    className={`rounded-md px-2 py-1.5 text-[11px] ${
                                                        focusHops === 1
                                                            ? 'bg-indigo-500/20 text-indigo-200'
                                                            : 'text-zinc-300 hover:bg-zinc-800'
                                                    }`}
                                                    title="1-hop focus neighborhood"
                                                >
                                                    1-hop
                                                </button>
                                                <button
                                                    type="button"
                                                    onClick={() => setFocusHops(2)}
                                                    className={`rounded-md px-2 py-1.5 text-[11px] ${
                                                        focusHops === 2
                                                            ? 'bg-indigo-500/20 text-indigo-200'
                                                            : 'text-zinc-300 hover:bg-zinc-800'
                                                    }`}
                                                    title="2-hop focus neighborhood"
                                                >
                                                    2-hop
                                                </button>
                                            </>
                                        )}
                                    </div>

                                    {currentScope && (
                                        <button
                                            type="button"
                                            onClick={handleBackToOverview}
                                            className="inline-flex items-center gap-1.5 rounded-lg border border-zinc-700 bg-zinc-900/85 px-2.5 py-2 text-xs text-zinc-200 hover:bg-zinc-800"
                                            title="Back to module overview"
                                        >
                                            <ArrowLeft size={13} />
                                            <span className="hidden sm:inline">Back to Overview</span>
                                            <span className="sm:hidden">Back</span>
                                        </button>
                                    )}
                                </div>

                                <GraphToolbar
                                    onFit={handleFit}
                                    onCenter={handleCenter}
                                    onRegenerate={handleRegenerate}
                                    onExport={handleExport}
                                    onToggleMiniMap={() => setShowMiniMap((prev) => !prev)}
                                    miniMapVisible={showMiniMap}
                                    isExporting={isExporting}
                                    isLoading={loading}
                                    disabled={loading}
                                />
                            </div>
                        </motion.div>

                        <GraphLegend
                            counts={typeCounts}
                            activeTypes={activeTypes}
                            onToggleType={handleToggleType}
                            onReset={() => setActiveTypes(new Set(ALL_FILE_TYPES))}
                            topOffset={headerHeight}
                        />

                        <AnimatePresence>
                            {loading && (
                                <motion.div
                                    initial={{ opacity: 0 }}
                                    animate={{ opacity: 1 }}
                                    exit={{ opacity: 0 }}
                                    className="absolute inset-0 z-30 flex items-center justify-center bg-zinc-950/92 backdrop-blur-sm"
                                >
                                    <div className="text-center">
                                        <Loader2 className="mx-auto mb-3 animate-spin text-indigo-400" size={34} />
                                        <p className="text-sm text-zinc-300">Building dependency graph...</p>
                                        <p className="mt-1 text-xs text-zinc-500">
                                            {currentView === 'module' ? 'Module overview generation' : 'Deterministic extraction and ranking'}
                                        </p>
                                    </div>
                                </motion.div>
                            )}
                        </AnimatePresence>

                        {!loading && error && (
                            <div className="absolute inset-0 z-20 flex items-center justify-center">
                                <div className="rounded-xl border border-rose-500/30 bg-zinc-900/95 px-6 py-5 text-center">
                                    <p className="text-sm text-rose-300">{error}</p>
                                    <button
                                        type="button"
                                        onClick={handleRegenerate}
                                        className="mt-3 rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-500"
                                    >
                                        Retry
                                    </button>
                                </div>
                            </div>
                        )}

                        {!loading && !error && renderedNodes.every((node) => node.hidden) && (
                            <div className="absolute inset-0 z-20 flex items-center justify-center">
                                <div className="rounded-xl border border-zinc-800 bg-zinc-900/90 px-6 py-5 text-center">
                                    <p className="text-sm text-zinc-300">No nodes match your current filters.</p>
                                    <button
                                        type="button"
                                        onClick={() => {
                                            setSearchQuery('');
                                            setActiveTypes(new Set(ALL_FILE_TYPES));
                                            resetFocusState();
                                        }}
                                        className="mt-3 rounded-md border border-zinc-700 px-3 py-1.5 text-xs text-zinc-300 hover:bg-zinc-800"
                                    >
                                        Reset filters
                                    </button>
                                </div>
                            </div>
                        )}

                        <ReactFlow<CustomFlowNode, CustomFlowEdge>
                            nodes={renderedNodes}
                            edges={renderedEdges}
                            nodeTypes={nodeTypes}
                            edgeTypes={edgeTypes}
                            onNodesChange={onNodesChange}
                            onEdgesChange={onEdgesChange}
                            onNodeClick={(_, node) => handleSelectNode(node.id)}
                            onInit={setFlowInstance}
                            onMoveEnd={handleViewportChange}
                            minZoom={0.15}
                            maxZoom={2.2}
                            fitView
                            fitViewOptions={{ padding: 0.2 }}
                            colorMode="dark"
                            onlyRenderVisibleElements
                            proOptions={{ hideAttribution: true }}
                            defaultEdgeOptions={{
                                type: 'custom',
                                markerEnd: { type: MarkerType.ArrowClosed, color: '#52525b' },
                            }}
                        >
                            <Background variant={BackgroundVariant.Dots} gap={22} size={1.1} color="#27272a" />
                            <Controls
                                className="!rounded-lg !border-zinc-800 !bg-zinc-900/90 !shadow-xl [&>button]:!border-zinc-700 [&>button]:!bg-zinc-800 [&>button:hover]:!bg-zinc-700"
                                position="bottom-right"
                            />
                            {showMiniMap && (
                                <MiniMap
                                    nodeColor={getMinimapNodeColor}
                                    maskColor="rgba(9, 9, 11, 0.75)"
                                    className="!rounded-lg !border-zinc-800 !bg-zinc-900/90"
                                    position="bottom-right"
                                    style={{ marginBottom: 70 }}
                                />
                            )}
                        </ReactFlow>
                    </div>

                    <NodeDetailPanel
                        repoId={repoId}
                        node={selectedNodeData}
                        incomingEdges={incomingEdges}
                        outgoingEdges={outgoingEdges}
                        onNodeClick={handleSelectNode}
                        onDrillDownModule={handleDrillDownModule}
                        open={inspectorOpen}
                        onToggleOpen={() => setInspectorOpen((prev) => !prev)}
                    />
                </div>
            </div>
        </ReactFlowProvider>
    );
}
