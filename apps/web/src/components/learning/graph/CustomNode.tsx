'use client';

import { memo } from 'react';
import { Handle, Position, NodeProps } from '@xyflow/react';
import { motion } from 'framer-motion';
import {
    Component,
    Layout,
    Database,
    Code,
    Server,
    Settings,
    FileText,
    Layers
} from 'lucide-react';

// File type configuration
export const FILE_TYPES = {
    component: {
        color: '#8B5CF6',
        gradient: 'from-violet-500/20 to-violet-600/10',
        borderColor: 'border-violet-500/50',
        icon: Component,
        label: 'Component'
    },
    page: {
        color: '#3B82F6',
        gradient: 'from-blue-500/20 to-blue-600/10',
        borderColor: 'border-blue-500/50',
        icon: Layout,
        label: 'Page'
    },
    store: {
        color: '#F59E0B',
        gradient: 'from-amber-500/20 to-amber-600/10',
        borderColor: 'border-amber-500/50',
        icon: Database,
        label: 'Store'
    },
    util: {
        color: '#10B981',
        gradient: 'from-emerald-500/20 to-emerald-600/10',
        borderColor: 'border-emerald-500/50',
        icon: Code,
        label: 'Utility'
    },
    api: {
        color: '#EC4899',
        gradient: 'from-pink-500/20 to-pink-600/10',
        borderColor: 'border-pink-500/50',
        icon: Server,
        label: 'API'
    },
    config: {
        color: '#6B7280',
        gradient: 'from-gray-500/20 to-gray-600/10',
        borderColor: 'border-gray-500/50',
        icon: Settings,
        label: 'Config'
    },
    schema: {
        color: '#06B6D4',
        gradient: 'from-cyan-500/20 to-cyan-600/10',
        borderColor: 'border-cyan-500/50',
        icon: Layers,
        label: 'Schema'
    },
    default: {
        color: '#A855F7',
        gradient: 'from-purple-500/20 to-purple-600/10',
        borderColor: 'border-purple-500/50',
        icon: FileText,
        label: 'File'
    }
} as const;

export type FileType = keyof typeof FILE_TYPES;

// Detect file type from path
export function detectFileType(filePath: string): FileType {
    const path = filePath.toLowerCase();
    const fileName = path.split('/').pop() || '';

    // Check path patterns
    if (path.includes('/components/') || fileName.endsWith('.component.tsx') || fileName.endsWith('.component.ts')) {
        return 'component';
    }
    if (path.includes('/pages/') || path.includes('/app/') && (fileName === 'page.tsx' || fileName === 'page.ts' || path.includes('page'))) {
        return 'page';
    }
    if (path.includes('/store') || path.includes('store.ts') || path.includes('zustand') || path.includes('redux')) {
        return 'store';
    }
    if (path.includes('/api/') || path.includes('routes') || path.includes('service')) {
        return 'api';
    }
    if (path.includes('/utils/') || path.includes('/lib/') || path.includes('/helpers/') || path.includes('util')) {
        return 'util';
    }
    if (path.includes('config') || path.includes('.config.') || fileName.startsWith('next.') || fileName.startsWith('tailwind.')) {
        return 'config';
    }
    if (path.includes('schema') || path.includes('types') || path.includes('interface')) {
        return 'schema';
    }
    if (path.includes('layout')) {
        return 'page';
    }

    return 'default';
}

// Custom node data interface - must have index signature for ReactFlow
export interface CustomNodeData {
    label: string;
    description?: string;
    filePath: string;
    fileType?: FileType;
    linesOfCode?: number;
    importance?: number;  // 1-10 scale for node sizing
    group?: string;       // folder/feature cluster
    exports?: string[];   // exported functions/classes
    isSelected?: boolean;
    isHighlighted?: boolean;
    [key: string]: unknown; // Index signature for ReactFlow compatibility
}

// Get size multiplier based on importance (1-10)
function getImportanceSizeMultiplier(importance?: number): number {
    if (!importance) return 1;
    // Scale from 0.85 (importance=1) to 1.25 (importance=10)
    return 0.85 + (importance - 1) * 0.044;
}

// Custom Node Component
function CustomNodeComponent({ data, selected }: { data: CustomNodeData; selected?: boolean }) {
    const fileType = data.fileType || detectFileType(data.filePath || data.label);
    const config = FILE_TYPES[fileType];
    const Icon = config.icon;
    const sizeMultiplier = getImportanceSizeMultiplier(data.importance);

    return (
        <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3, ease: 'easeOut' }}
            className={`
                relative group cursor-pointer
                bg-gradient-to-br ${config.gradient}
                backdrop-blur-sm
                border ${config.borderColor}
                ${selected ? 'ring-2 ring-offset-2 ring-offset-zinc-950' : ''}
                rounded-xl px-4 py-3
                transition-all duration-200
                hover:scale-105 hover:shadow-lg
            `}
            style={{
                minWidth: `${Math.round(180 * sizeMultiplier)}px`,
                maxWidth: `${Math.round(240 * sizeMultiplier)}px`,
                boxShadow: selected
                    ? `0 0 20px ${config.color}40, 0 0 40px ${config.color}20`
                    : data.isHighlighted
                        ? `0 0 15px ${config.color}30`
                        : data.importance && data.importance >= 8
                            ? `0 0 12px ${config.color}25`
                            : 'none',
                borderColor: config.color,
                borderWidth: data.importance && data.importance >= 7 ? '2px' : '1px',
            }}
        >
            {/* Glow effect on hover */}
            <div
                className="absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"
                style={{
                    background: `radial-gradient(circle at center, ${config.color}15 0%, transparent 70%)`,
                }}
            />

            {/* Handles for connections */}
            <Handle
                type="target"
                position={Position.Left}
                className="!w-3 !h-3 !bg-zinc-700 !border-2 !border-zinc-500 group-hover:!border-indigo-400 transition-colors"
            />
            <Handle
                type="source"
                position={Position.Right}
                className="!w-3 !h-3 !bg-zinc-700 !border-2 !border-zinc-500 group-hover:!border-indigo-400 transition-colors"
            />

            {/* Content */}
            <div className="relative z-10 flex items-center gap-3">
                {/* Icon */}
                <div
                    className="flex-shrink-0 p-2 rounded-lg"
                    style={{ backgroundColor: `${config.color}20` }}
                >
                    <Icon size={18} style={{ color: config.color }} />
                </div>

                {/* Label and type */}
                <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">
                        {data.label}
                    </p>
                    <p className="text-xs text-zinc-500 truncate">
                        {config.label}
                    </p>
                </div>
            </div>

            {/* Tooltip on hover */}
            {data.description && (
                <div className="absolute left-1/2 -translate-x-1/2 bottom-full mb-2 px-3 py-2 bg-zinc-900 border border-zinc-700 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50 w-64 text-center shadow-xl">
                    <p className="text-xs text-zinc-300">{data.description}</p>
                    <div className="absolute left-1/2 -translate-x-1/2 top-full w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-zinc-700" />
                </div>
            )}

            {/* Lines of code badge */}
            {data.linesOfCode && (
                <div className="absolute -top-2 -right-2 px-1.5 py-0.5 bg-zinc-800 border border-zinc-700 rounded text-[10px] text-zinc-400 font-mono">
                    {data.linesOfCode} LOC
                </div>
            )}

            {/* Importance indicator for high-importance nodes */}
            {data.importance && data.importance >= 8 && (
                <div className="absolute -top-2 -left-2 w-4 h-4 rounded-full flex items-center justify-center text-[9px] font-bold text-white"
                    style={{ backgroundColor: config.color }}
                >
                    ★
                </div>
            )}
        </motion.div>
    );
}

export const CustomNode = memo(CustomNodeComponent);
