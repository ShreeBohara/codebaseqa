'use client';

import { memo } from 'react';
import { BaseEdge, Edge, EdgeLabelRenderer, EdgeProps, getBezierPath } from '@xyflow/react';
import { motion } from 'framer-motion';

// Edge type configuration
export const EDGE_TYPES = {
    imports: {
        color: '#6366f1',
        style: 'solid',
        animated: true,
        label: 'imports'
    },
    uses: {
        color: '#06b6d4',
        style: 'dashed',
        animated: false,
        label: 'uses'
    },
    extends: {
        color: '#8b5cf6',
        style: 'solid',
        animated: true,
        label: 'extends'
    },
    implements: {
        color: '#10b981',
        style: 'dotted',
        animated: false,
        label: 'implements'
    },
    calls: {
        color: '#f59e0b',
        style: 'solid',
        animated: true,
        label: 'calls'
    },
    configures: {
        color: '#ec4899',
        style: 'dashed',
        animated: false,
        label: 'configures'
    }
} as const;

export type EdgeType = keyof typeof EDGE_TYPES;

export interface CustomEdgeData {
    label?: string;
    type?: EdgeType;
    weight?: number;  // 1-5 for edge thickness
    isHighlighted?: boolean;
    [key: string]: unknown;
}

export type CustomFlowEdge = Edge<CustomEdgeData, 'custom'>;

// Get stroke width based on weight (1-5)
function getWeightedStrokeWidth(weight?: number, isHighlighted?: boolean): number {
    const baseWidth = isHighlighted ? 3 : 2;
    if (!weight) return baseWidth;
    // Scale from 1.5 (weight=1) to 4 (weight=5)
    return 1.5 + (weight - 1) * 0.625 + (isHighlighted ? 1 : 0);
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
        curvature: 0.25,
    });

    const isHighlighted = data?.isHighlighted || selected;

    return (
        <>
            {/* Glow effect for highlighted edges */}
            {isHighlighted && (
                <path
                    d={edgePath}
                    fill="none"
                    stroke={config.color}
                    strokeWidth={8}
                    strokeOpacity={0.3}
                    filter="blur(4px)"
                />
            )}

            {/* Main edge path */}
            <BaseEdge
                id={id}
                path={edgePath}
                markerEnd={markerEnd}
                style={{
                    stroke: config.color,
                    strokeWidth: getWeightedStrokeWidth(data?.weight, isHighlighted),
                    strokeDasharray: config.style === 'dashed' ? '8,4' : config.style === 'dotted' ? '2,4' : 'none',
                    transition: 'stroke-width 0.2s ease',
                }}
            />

            {/* Animated dot flowing along the edge */}
            {config.animated && (
                <motion.circle
                    r={4}
                    fill={config.color}
                    filter={`drop-shadow(0 0 4px ${config.color})`}
                    initial={{ offsetDistance: '0%' }}
                    animate={{ offsetDistance: '100%' }}
                    transition={{
                        duration: 2,
                        repeat: Infinity,
                        ease: 'linear',
                    }}
                    style={{
                        offsetPath: `path('${edgePath}')`,
                    }}
                />
            )}

            {/* Edge label */}
            {data?.label && (
                <EdgeLabelRenderer>
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="nodrag nopan pointer-events-auto"
                        style={{
                            position: 'absolute',
                            transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)`,
                        }}
                    >
                        <div
                            className={`
                                px-2 py-0.5 rounded-full text-[10px] font-medium
                                border backdrop-blur-sm
                                ${isHighlighted ? 'bg-zinc-800/90' : 'bg-zinc-900/80'}
                            `}
                            style={{
                                color: config.color,
                                borderColor: `${config.color}40`,
                            }}
                        >
                            {data.label}
                        </div>
                    </motion.div>
                </EdgeLabelRenderer>
            )}
        </>
    );
}

export const CustomEdge = memo(CustomEdgeComponent);
