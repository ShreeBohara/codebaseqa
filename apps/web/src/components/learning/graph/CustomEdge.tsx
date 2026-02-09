'use client';

import { memo } from 'react';
import { BaseEdge, Edge, EdgeLabelRenderer, EdgeProps, getBezierPath } from '@xyflow/react';

export const EDGE_TYPES = {
    imports: { color: '#818cf8', style: 'solid', label: 'imports' },
    uses: { color: '#22d3ee', style: 'dashed', label: 'uses' },
    extends: { color: '#c084fc', style: 'solid', label: 'extends' },
    calls: { color: '#f59e0b', style: 'solid', label: 'calls' },
    configures: { color: '#f472b6', style: 'dashed', label: 'configures' },
} as const;

export type EdgeType = keyof typeof EDGE_TYPES;

export interface CustomEdgeData {
    label?: string;
    type?: EdgeType;
    relation?: string;
    weight?: number;
    confidence?: number;
    rank?: number;
    zoomLevel?: number;
    isDimmed?: boolean;
    isHighlighted?: boolean;
    [key: string]: unknown;
}

export type CustomFlowEdge = Edge<CustomEdgeData, 'custom'>;

function getStrokeWidth(weight?: number, highlighted?: boolean): number {
    const base = highlighted ? 2.2 : 1.3;
    if (!weight) return base;
    return base + Math.min(2, weight * 0.35);
}

function CustomEdgeComponent({
    id,
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    data,
    selected,
    markerEnd,
}: EdgeProps<CustomFlowEdge>) {
    const edgeType = (data?.type as EdgeType) || 'imports';
    const config = EDGE_TYPES[edgeType] || EDGE_TYPES.imports;

    const [edgePath, labelX, labelY] = getBezierPath({
        sourceX,
        sourceY,
        sourcePosition,
        targetX,
        targetY,
        targetPosition,
        curvature: 0.23,
    });

    const highlighted = Boolean(selected || data?.isHighlighted);
    const zoomLevel = data?.zoomLevel ?? 1;
    const isDimmed = Boolean(data?.isDimmed && !highlighted);
    const showLabel = highlighted || (((data?.weight ?? 0) >= 4 || (data?.rank ?? 0) >= 0.82) && zoomLevel >= 0.9);

    return (
        <>
            {highlighted && (
                <path
                    d={edgePath}
                    fill="none"
                    stroke={config.color}
                    strokeWidth={6.5}
                    strokeOpacity={0.16}
                    filter="blur(3px)"
                />
            )}

            <BaseEdge
                id={id}
                path={edgePath}
                markerEnd={markerEnd}
                style={{
                    stroke: config.color,
                    strokeOpacity: highlighted ? 0.95 : isDimmed ? 0.1 : 0.24,
                    strokeWidth: getStrokeWidth(data?.weight, highlighted),
                    strokeDasharray: config.style === 'dashed' ? '6,5' : 'none',
                    transition: 'stroke-opacity 120ms ease, stroke-width 120ms ease',
                }}
            />

            {showLabel && (
                <EdgeLabelRenderer>
                    <div
                        className="nodrag nopan"
                        style={{
                            position: 'absolute',
                            transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
                        }}
                    >
                        <div
                            className="rounded-md border px-1.5 py-0.5 text-[10px] font-medium backdrop-blur-sm"
                            style={{
                                color: config.color,
                                borderColor: `${config.color}55`,
                                background: 'rgba(9, 9, 11, 0.86)',
                            }}
                        >
                            {data?.relation || data?.label || config.label}
                        </div>
                    </div>
                </EdgeLabelRenderer>
            )}
        </>
    );
}

export const CustomEdge = memo(CustomEdgeComponent);
