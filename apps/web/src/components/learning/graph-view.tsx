'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
    Background,
    BackgroundVariant,
    Controls,
    EdgeTypes,
    MiniMap,
    Node,
    NodeTypes,
    ReactFlow,
    ReactFlowProvider,
    useEdgesState,
    useNodesState,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { toPng } from 'html-to-image';
import { motion, AnimatePresence } from 'framer-motion';
import { api, DependencyGraph } from '@/lib/api-client';
import { Loader2, RefreshCw, Search, X, Sparkles } from 'lucide-react';

// Import custom components
import { CustomFlowNode, CustomNode, CustomNodeData, FILE_TYPES, detectFileType } from './graph/CustomNode';
import { CustomEdge, CustomFlowEdge, EdgeType } from './graph/CustomEdge';
import { GraphLegend } from './graph/GraphLegend';
import { NodeDetailPanel } from './graph/NodeDetailPanel';
import { GraphToolbar, LayoutType } from './graph/GraphToolbar';
import { applyLayout } from './graph/graph-layouts';

interface GraphViewProps {
    repoId: string;
}

// Register custom node and edge types
const nodeTypes = {
    custom: CustomNode,
} as unknown as NodeTypes;

const edgeTypes = {
    custom: CustomEdge,
} as unknown as EdgeTypes;

export function GraphView({ repoId }: GraphViewProps) {
    const [nodes, setNodes, onNodesChange] = useNodesState<CustomFlowNode>([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState<CustomFlowEdge>([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const [selectedNode, setSelectedNode] = useState<string | null>(null);
    const [currentLayout, setCurrentLayout] = useState<LayoutType>('hierarchy');
    const [isExporting, setIsExporting] = useState(false);

    // Refs
    const hasFetchedRef = useRef(false);
    const isFetchingRef = useRef(false);
    const containerRef = useRef<HTMLDivElement>(null);
    const rawNodesRef = useRef<CustomFlowNode[]>([]);  // Store nodes without layout
    const rawEdgesRef = useRef<CustomFlowEdge[]>([]);  // Store edges

    const loadGraph = useCallback(async (force = false) => {
        // Prevent concurrent fetches
        if (isFetchingRef.current && !force) return;

        // Skip if already fetched and not forcing
        if (hasFetchedRef.current && !force) return;

        isFetchingRef.current = true;
        setLoading(true);

        try {
            const data: DependencyGraph = await api.getDependencyGraph(repoId);

            if (!data.nodes || data.nodes.length === 0) {
                setNodes([]);
                setEdges([]);
                return;
            }

            // Create nodes with custom type and data (including enhanced fields)
            const initialNodes: CustomFlowNode[] = data.nodes.map((node) => {
                const normalizedType = node.type as keyof typeof FILE_TYPES;
                const fileType = normalizedType in FILE_TYPES ? normalizedType : detectFileType(node.id);

                return {
                    id: node.id,
                    type: 'custom',
                    data: {
                        label: node.label || node.id.split('/').pop() || node.id,
                        description: node.description,
                        filePath: node.id,
                        fileType,
                        importance: node.importance,
                        linesOfCode: node.loc,
                        group: node.group,
                        exports: node.exports,
                    },
                    position: { x: 0, y: 0 },
                };
            });

            // Filter and create edges with enhanced data
            const nodeIds = new Set(initialNodes.map((node) => node.id));
            const initialEdges: CustomFlowEdge[] = (data.edges || [])
                .filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target))
                .map((edge) => ({
                    id: `${edge.source}-${edge.target}`,
                    source: edge.source,
                    target: edge.target,
                    type: 'custom',
                    data: {
                        label: edge.label || 'imports',
                        type: (edge.type || 'imports') as EdgeType,
                        weight: edge.weight,
                    },
                    animated: true,
                }));

            // Store raw nodes/edges for layout switching
            rawNodesRef.current = initialNodes;
            rawEdgesRef.current = initialEdges;

            // Apply layout
            const layoutedNodes = applyLayout(initialNodes, initialEdges, currentLayout);

            setNodes(layoutedNodes);
            setEdges(initialEdges);
            hasFetchedRef.current = true;
        } catch (error) {
            console.error('Failed to load graph:', error);
            setNodes([]);
            setEdges([]);
        } finally {
            setLoading(false);
            isFetchingRef.current = false;
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [repoId]);

    useEffect(() => {
        loadGraph();
    }, [loadGraph]);

    // Filter nodes based on search
    const filteredNodes = searchQuery
        ? nodes.filter((node) =>
            node.data.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
            node.data.filePath.toLowerCase().includes(searchQuery.toLowerCase())
        )
        : nodes;

    // Minimap node color function
    const getMinimapNodeColor = (node: Node) => {
        const nodeData = node.data as CustomNodeData | undefined;
        const fileType = nodeData?.fileType || 'default';
        return FILE_TYPES[fileType]?.color || '#6366f1';
    };

    // Get selected node data
    const selectedNodeData = selectedNode ? nodes.find((node) => node.id === selectedNode) ?? null : null;

    // Compute incoming and outgoing edges for selected node
    const incomingEdges = selectedNode
        ? edges
            .filter((edge) => edge.target === selectedNode)
            .map((edge) => ({
                source: edge.source,
                label: typeof edge.data?.label === 'string' ? edge.data.label : undefined,
            }))
        : [];

    const outgoingEdges = selectedNode
        ? edges
            .filter((edge) => edge.source === selectedNode)
            .map((edge) => ({
                target: edge.target,
                label: typeof edge.data?.label === 'string' ? edge.data.label : undefined,
            }))
        : [];

    // Handle layout change
    const handleLayoutChange = useCallback((layout: LayoutType) => {
        setCurrentLayout(layout);
        if (rawNodesRef.current.length > 0) {
            const layoutedNodes = applyLayout(rawNodesRef.current, rawEdgesRef.current, layout);
            setNodes(layoutedNodes);
        }
    }, [setNodes]);

    // Handle PNG export
    const handleExport = useCallback(async () => {
        if (!containerRef.current) return;
        setIsExporting(true);
        try {
            const dataUrl = await toPng(containerRef.current.querySelector('.react-flow') as HTMLElement, {
                backgroundColor: '#09090b',
                quality: 1,
            });
            const link = document.createElement('a');
            link.download = 'dependency-graph.png';
            link.href = dataUrl;
            link.click();
        } catch (error) {
            console.error('Failed to export graph:', error);
        } finally {
            setIsExporting(false);
        }
    }, []);

    return (
        <ReactFlowProvider>
            <div
                ref={containerRef}
                style={{
                    width: '100%',
                    height: 'calc(100vh - 150px)',
                    minHeight: '500px',
                }}
                className="bg-zinc-950 relative rounded-xl overflow-hidden"
            >
                {/* Top Toolbar */}
                <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="absolute top-4 left-4 right-4 z-50 flex items-center justify-between gap-4"
                >
                    {/* Search Input */}
                    <div className="relative flex-1 max-w-xs">
                        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
                        <input
                            type="text"
                            value={searchQuery}
                            onChange={(event) => setSearchQuery(event.target.value)}
                            placeholder="Search nodes..."
                            className="w-full pl-9 pr-8 py-2 bg-zinc-900/90 backdrop-blur-sm border border-zinc-800 rounded-lg text-sm text-white placeholder:text-zinc-500 focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/20 transition-all"
                        />
                        {searchQuery && (
                            <button
                                onClick={() => setSearchQuery('')}
                                className="absolute right-2 top-1/2 -translate-y-1/2 p-1 hover:bg-zinc-800 rounded transition-colors"
                            >
                                <X size={12} className="text-zinc-500" />
                            </button>
                        )}
                    </div>

                    {/* Stats Badge with Density Indicator */}
                    <div className="flex items-center gap-2 px-3 py-1.5 bg-zinc-900/90 backdrop-blur-sm border border-zinc-800 rounded-lg">
                        <Sparkles size={12} className="text-indigo-400" />
                        <span className="text-xs text-zinc-400">
                            {nodes.length} nodes • {edges.length} connections
                        </span>
                        {nodes.length > 0 && (
                            <span className={`text-xs px-1.5 py-0.5 rounded ${
                                edges.length / nodes.length >= 1.5
                                    ? 'bg-emerald-500/20 text-emerald-400'
                                    : edges.length / nodes.length >= 1.0
                                        ? 'bg-amber-500/20 text-amber-400'
                                        : 'bg-red-500/20 text-red-400'
                            }`}>
                                {(edges.length / nodes.length).toFixed(1)} e/n
                            </span>
                        )}
                    </div>

                    {/* Regenerate Button */}
                    <button
                        onClick={() => loadGraph(true)}
                        disabled={loading}
                        className="flex items-center gap-2 px-3 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors shadow-lg shadow-indigo-500/20"
                    >
                        {loading ? (
                            <Loader2 className="animate-spin" size={14} />
                        ) : (
                            <RefreshCw size={14} />
                        )}
                        <span>Regenerate</span>
                    </button>
                </motion.div>

                {/* Loading Overlay */}
                <AnimatePresence>
                    {loading && (
                        <motion.div
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="absolute inset-0 flex items-center justify-center z-40 bg-zinc-950/90 backdrop-blur-sm"
                        >
                            <motion.div
                                initial={{ scale: 0.9 }}
                                animate={{ scale: 1 }}
                                className="flex flex-col items-center gap-4"
                            >
                                <div className="relative">
                                    <Loader2 className="animate-spin text-indigo-500" size={48} />
                                    <div className="absolute inset-0 blur-xl bg-indigo-500/30 rounded-full" />
                                </div>
                                <div className="text-center">
                                    <p className="text-white font-medium">Analyzing codebase...</p>
                                    <p className="text-zinc-500 text-sm mt-1">
                                        Building dependency graph
                                    </p>
                                </div>
                            </motion.div>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Empty State */}
                {!loading && nodes.length === 0 && (
                    <div className="absolute inset-0 flex items-center justify-center z-30">
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            className="text-center bg-zinc-900/95 p-8 rounded-2xl border border-zinc-800 backdrop-blur shadow-2xl max-w-md"
                        >
                            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-indigo-500/20 to-purple-500/20 flex items-center justify-center">
                                <Sparkles className="text-indigo-400" size={28} />
                            </div>
                            <h3 className="text-lg font-semibold text-white mb-2">
                                No Dependency Map Yet
                            </h3>
                            <p className="text-zinc-400 text-sm mb-6">
                                Generate an AI-powered visualization of your codebase architecture.
                            </p>
                            <button
                                onClick={() => loadGraph(true)}
                                className="px-6 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white rounded-xl text-sm font-medium transition-all shadow-lg shadow-indigo-500/25"
                            >
                                Generate Graph
                            </button>
                        </motion.div>
                    </div>
                )}

                {/* Legend */}
                <GraphLegend />

                {/* ReactFlow Canvas */}
                <ReactFlow<CustomFlowNode, CustomFlowEdge>
                    nodes={searchQuery ? filteredNodes : nodes}
                    edges={edges}
                    nodeTypes={nodeTypes}
                    edgeTypes={edgeTypes}
                    onNodesChange={onNodesChange}
                    onEdgesChange={onEdgesChange}
                    onNodeClick={(_, node) => setSelectedNode(node.id)}
                    fitView
                    fitViewOptions={{ padding: 0.2 }}
                    colorMode="dark"
                    minZoom={0.1}
                    maxZoom={2}
                    proOptions={{ hideAttribution: true }}
                    defaultEdgeOptions={{
                        type: 'custom',
                        animated: true,
                    }}
                >
                    <Background
                        variant={BackgroundVariant.Dots}
                        gap={20}
                        size={1}
                        color="#27272a"
                    />
                    <Controls
                        className="!bg-zinc-900/90 !border-zinc-800 !rounded-lg !shadow-xl [&>button]:!bg-zinc-800 [&>button]:!border-zinc-700 [&>button]:!rounded [&>button:hover]:!bg-zinc-700 [&>button]:!fill-zinc-400"
                        position="bottom-right"
                    />
                    <MiniMap
                        nodeColor={getMinimapNodeColor}
                        maskColor="rgba(0, 0, 0, 0.8)"
                        className="!bg-zinc-900/90 !border-zinc-800 !rounded-lg"
                        position="bottom-right"
                        style={{ marginBottom: 150 }}
                    />
                </ReactFlow>

                {/* Node Detail Panel */}
                <NodeDetailPanel
                    node={selectedNodeData}
                    onClose={() => setSelectedNode(null)}
                    incomingEdges={incomingEdges}
                    outgoingEdges={outgoingEdges}
                    onNodeClick={(nodeId) => setSelectedNode(nodeId)}
                />

                {/* Bottom Toolbar */}
                {nodes.length > 0 && (
                    <GraphToolbar
                        currentLayout={currentLayout}
                        onLayoutChange={handleLayoutChange}
                        onExport={handleExport}
                        isExporting={isExporting}
                        disabled={loading}
                    />
                )}
            </div>
        </ReactFlowProvider>
    );
}
