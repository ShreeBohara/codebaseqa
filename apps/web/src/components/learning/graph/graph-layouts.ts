import dagre from 'dagre';
import { Edge, Node, Position } from '@xyflow/react';

const DEFAULT_NODE_WIDTH = 270;
const DEFAULT_NODE_HEIGHT = 92;
const DEFAULT_MODULE_WIDTH = 240;
const DEFAULT_MODULE_HEIGHT = 84;
const ELK_TIMEOUT_MS = 1500;
const LAYOUT_CACHE_MAX_ENTRIES = 48;

type CachedPosition = {
    x: number;
    y: number;
};

const layoutCache = new Map<string, Record<string, CachedPosition>>();
let elkInstance: { layout: (graph: unknown) => Promise<{ children?: Array<{ id?: string; x?: number; y?: number }> }> } | null | undefined;

async function getElkInstance() {
    if (elkInstance !== undefined) {
        return elkInstance;
    }
    try {
        const dynamicImporter = new Function('modulePath', 'return import(modulePath);') as (modulePath: string) => Promise<unknown>;
        const mod = await dynamicImporter('elkjs/lib/elk.bundled.js');
        const ctor = (mod as { default?: new () => { layout: (graph: unknown) => Promise<unknown> } }).default
            || (mod as new () => { layout: (graph: unknown) => Promise<unknown> });
        elkInstance = new ctor() as {
            layout: (graph: unknown) => Promise<{ children?: Array<{ id?: string; x?: number; y?: number }> }>;
        };
        return elkInstance;
    } catch {
        elkInstance = null;
        return null;
    }
}

function nodeDimensions(node: Node): { width: number; height: number } {
    const entity = (node.data as { entity?: string } | undefined)?.entity;
    if (entity === 'module') {
        return { width: DEFAULT_MODULE_WIDTH, height: DEFAULT_MODULE_HEIGHT };
    }
    return { width: DEFAULT_NODE_WIDTH, height: DEFAULT_NODE_HEIGHT };
}

function graphSignature<T extends Node, E extends Edge>(nodes: T[], edges: E[]): string {
    const nodeSig = [...nodes]
        .map((node) => {
            const data = node.data as { entity?: string; group?: string } | undefined;
            return `${node.id}:${data?.entity || 'file'}:${data?.group || ''}`;
        })
        .sort()
        .join('|');
    const edgeSig = [...edges]
        .map((edge) => `${edge.source}->${edge.target}:${(edge.data as { relation?: string } | undefined)?.relation || ''}`)
        .sort()
        .join('|');
    return `${nodeSig}::${edgeSig}`;
}

function setCachedLayout(signature: string, positions: Record<string, CachedPosition>) {
    layoutCache.set(signature, positions);
    if (layoutCache.size <= LAYOUT_CACHE_MAX_ENTRIES) {
        return;
    }
    const staleKey = layoutCache.keys().next().value as string | undefined;
    if (staleKey) {
        layoutCache.delete(staleKey);
    }
}

function applyPositions<T extends Node>(
    nodes: T[],
    positions: Record<string, CachedPosition>
): T[] {
    return nodes.map((node) => {
        const dims = nodeDimensions(node);
        const position = positions[node.id];
        if (!position) {
            return {
                ...node,
                targetPosition: Position.Left,
                sourcePosition: Position.Right,
            };
        }
        return {
            ...node,
            targetPosition: Position.Left,
            sourcePosition: Position.Right,
            position: {
                x: position.x - dims.width / 2,
                y: position.y - dims.height / 2,
            },
        };
    });
}

function buildDagreFallbackLayout<T extends Node, E extends Edge>(nodes: T[], edges: E[]): Record<string, CachedPosition> {
    const dagreGraph = new dagre.graphlib.Graph();
    dagreGraph.setDefaultEdgeLabel(() => ({}));
    dagreGraph.setGraph({
        rankdir: 'LR',
        align: 'UL',
        nodesep: 92,
        ranksep: 160,
        marginx: 40,
        marginy: 40,
        acyclicer: 'greedy',
    });

    const sortedNodes = [...nodes].sort((a, b) => a.id.localeCompare(b.id));
    const sortedEdges = [...edges].sort((a, b) => {
        const bySource = a.source.localeCompare(b.source);
        if (bySource !== 0) return bySource;
        return a.target.localeCompare(b.target);
    });

    sortedNodes.forEach((node) => {
        const dims = nodeDimensions(node);
        dagreGraph.setNode(node.id, { width: dims.width, height: dims.height });
    });
    sortedEdges.forEach((edge) => {
        dagreGraph.setEdge(edge.source, edge.target);
    });

    dagre.layout(dagreGraph);

    const positions: Record<string, CachedPosition> = {};
    sortedNodes.forEach((node) => {
        const pos = dagreGraph.node(node.id) ?? { x: 0, y: 0 };
        positions[node.id] = { x: pos.x, y: pos.y };
    });
    return positions;
}

async function buildElkLayout<T extends Node, E extends Edge>(nodes: T[], edges: E[]): Promise<Record<string, CachedPosition>> {
    const elk = await getElkInstance();
    if (!elk) {
        throw new Error('ELK unavailable');
    }

    const sortedNodes = [...nodes].sort((a, b) => a.id.localeCompare(b.id));
    const sortedEdges = [...edges].sort((a, b) => {
        const bySource = a.source.localeCompare(b.source);
        if (bySource !== 0) return bySource;
        return a.target.localeCompare(b.target);
    });

    const moduleNodeCount = sortedNodes.filter((node) => (node.data as { entity?: string } | undefined)?.entity === 'module').length;
    const isDenseFileScope = sortedNodes.length >= 120 && moduleNodeCount < Math.max(4, Math.floor(sortedNodes.length * 0.25));
    const hasHeavyEdgeLoad = sortedEdges.length > sortedNodes.length * 2;
    const layerSpacing = isDenseFileScope ? 188 : hasHeavyEdgeLoad ? 158 : 130;
    const nodeSpacing = isDenseFileScope ? 84 : hasHeavyEdgeLoad ? 72 : 68;

    const elkGraph = {
        id: 'root',
        layoutOptions: {
            'elk.algorithm': 'layered',
            'elk.direction': 'RIGHT',
            'elk.layered.spacing.nodeNodeBetweenLayers': String(layerSpacing),
            'elk.spacing.nodeNode': String(nodeSpacing),
            'elk.layered.crossingMinimization.strategy': 'LAYER_SWEEP',
            'elk.layered.nodePlacement.strategy': 'NETWORK_SIMPLEX',
            'elk.edgeRouting': 'ORTHOGONAL',
            'elk.padding': '[top=26,left=26,bottom=26,right=26]',
        },
        children: sortedNodes.map((node) => {
            const dims = nodeDimensions(node);
            return {
                id: node.id,
                width: dims.width,
                height: dims.height,
            };
        }),
        edges: sortedEdges.map((edge, index) => ({
            id: `e-${index}-${edge.source}-${edge.target}`,
            sources: [edge.source],
            targets: [edge.target],
        })),
    };

    const timeout = new Promise<never>((_, reject) => {
        setTimeout(() => reject(new Error('ELK layout timeout')), ELK_TIMEOUT_MS);
    });
    const result = await Promise.race([elk.layout(elkGraph), timeout]);

    const positionedChildren = Array.isArray(result.children) ? result.children : [];
    const positions: Record<string, CachedPosition> = {};
    positionedChildren.forEach((child: { id?: string; x?: number; y?: number }) => {
        if (!child.id) return;
        positions[child.id] = {
            x: child.x ?? 0,
            y: child.y ?? 0,
        };
    });
    return positions;
}

/**
 * Deterministic Graph V2.1 auto layout.
 * Primary layout: ELK (layered, orthogonal) with timeout guard.
 * Fallback: Dagre if ELK fails or times out.
 */
export async function applyAutoLayout<T extends Node, E extends Edge>(nodes: T[], edges: E[]): Promise<T[]> {
    if (nodes.length === 0) {
        return nodes;
    }

    const signature = graphSignature(nodes, edges);
    const cached = layoutCache.get(signature);
    if (cached) {
        return applyPositions(nodes, cached);
    }

    let positions: Record<string, CachedPosition>;
    try {
        positions = await buildElkLayout(nodes, edges);
    } catch {
        positions = buildDagreFallbackLayout(nodes, edges);
    }

    setCachedLayout(signature, positions);
    return applyPositions(nodes, positions);
}

// Backward-compatible export name for existing imports.
export const applyLayout = applyAutoLayout;
