import dagre from 'dagre';
import { LayoutType } from './GraphToolbar';

const nodeWidth = 200;
const nodeHeight = 70;

/**
 * Apply horizontal hierarchy layout using dagre (left-to-right)
 */
export function applyHierarchyLayout(nodes: any[], edges: any[]) {
    const dagreGraph = new dagre.graphlib.Graph();
    dagreGraph.setDefaultEdgeLabel(() => ({}));
    dagreGraph.setGraph({ rankdir: 'LR', nodesep: 80, ranksep: 120 });

    nodes.forEach((node) => {
        dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
    });

    edges.forEach((edge) => {
        dagreGraph.setEdge(edge.source, edge.target);
    });

    dagre.layout(dagreGraph);

    return nodes.map((node) => {
        const pos = dagreGraph.node(node.id);
        return {
            ...node,
            targetPosition: 'left',
            sourcePosition: 'right',
            position: {
                x: pos.x - nodeWidth / 2,
                y: pos.y - nodeHeight / 2,
            },
        };
    });
}

/**
 * Apply vertical tree layout using dagre (top-to-bottom)
 */
export function applyVerticalLayout(nodes: any[], edges: any[]) {
    const dagreGraph = new dagre.graphlib.Graph();
    dagreGraph.setDefaultEdgeLabel(() => ({}));
    dagreGraph.setGraph({ rankdir: 'TB', nodesep: 60, ranksep: 100 });

    nodes.forEach((node) => {
        dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
    });

    edges.forEach((edge) => {
        dagreGraph.setEdge(edge.source, edge.target);
    });

    dagre.layout(dagreGraph);

    return nodes.map((node) => {
        const pos = dagreGraph.node(node.id);
        return {
            ...node,
            targetPosition: 'top',
            sourcePosition: 'bottom',
            position: {
                x: pos.x - nodeWidth / 2,
                y: pos.y - nodeHeight / 2,
            },
        };
    });
}

/**
 * Apply radial layout - nodes arranged in circles around a center
 */
export function applyRadialLayout(nodes: any[], edges: any[]) {
    if (nodes.length === 0) return nodes;

    // Find the root node (node with most outgoing edges or first node)
    const outgoingCounts = new Map<string, number>();
    edges.forEach((edge) => {
        outgoingCounts.set(edge.source, (outgoingCounts.get(edge.source) || 0) + 1);
    });

    let rootId = nodes[0].id;
    let maxOutgoing = 0;
    outgoingCounts.forEach((count, id) => {
        if (count > maxOutgoing) {
            maxOutgoing = count;
            rootId = id;
        }
    });

    // Build adjacency list
    const children = new Map<string, string[]>();
    edges.forEach((edge) => {
        if (!children.has(edge.source)) {
            children.set(edge.source, []);
        }
        children.get(edge.source)!.push(edge.target);
    });

    // BFS to assign levels
    const levels = new Map<string, number>();
    const visited = new Set<string>();
    const queue: { id: string; level: number }[] = [{ id: rootId, level: 0 }];

    while (queue.length > 0) {
        const { id, level } = queue.shift()!;
        if (visited.has(id)) continue;
        visited.add(id);
        levels.set(id, level);

        const nodeChildren = children.get(id) || [];
        nodeChildren.forEach((childId) => {
            if (!visited.has(childId)) {
                queue.push({ id: childId, level: level + 1 });
            }
        });
    }

    // Add any unvisited nodes
    nodes.forEach((node) => {
        if (!visited.has(node.id)) {
            levels.set(node.id, (levels.size > 0 ? Math.max(...levels.values()) + 1 : 0));
        }
    });

    // Group nodes by level
    const levelGroups = new Map<number, string[]>();
    levels.forEach((level, id) => {
        if (!levelGroups.has(level)) {
            levelGroups.set(level, []);
        }
        levelGroups.get(level)!.push(id);
    });

    // Calculate positions
    const centerX = 400;
    const centerY = 300;
    const radiusStep = 180;
    const positions = new Map<string, { x: number; y: number }>();

    levelGroups.forEach((nodeIds, level) => {
        if (level === 0) {
            // Center node
            nodeIds.forEach((id) => {
                positions.set(id, { x: centerX, y: centerY });
            });
        } else {
            const radius = level * radiusStep;
            const angleStep = (2 * Math.PI) / nodeIds.length;
            nodeIds.forEach((id, index) => {
                const angle = index * angleStep - Math.PI / 2;
                positions.set(id, {
                    x: centerX + radius * Math.cos(angle),
                    y: centerY + radius * Math.sin(angle),
                });
            });
        }
    });

    return nodes.map((node) => {
        const pos = positions.get(node.id) || { x: 0, y: 0 };
        return {
            ...node,
            targetPosition: 'left',
            sourcePosition: 'right',
            position: {
                x: pos.x - nodeWidth / 2,
                y: pos.y - nodeHeight / 2,
            },
        };
    });
}

/**
 * Apply the specified layout to nodes
 */
export function applyLayout(nodes: any[], edges: any[], layout: LayoutType) {
    switch (layout) {
        case 'radial':
            return applyRadialLayout(nodes, edges);
        case 'vertical':
            return applyVerticalLayout(nodes, edges);
        case 'hierarchy':
        default:
            return applyHierarchyLayout(nodes, edges);
    }
}
