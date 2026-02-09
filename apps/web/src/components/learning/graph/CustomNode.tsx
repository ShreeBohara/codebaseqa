'use client';

import { memo } from 'react';
import { Handle, Node, NodeProps, Position } from '@xyflow/react';
import {
    Code,
    Component,
    Database,
    FileText,
    Layers,
    Layout,
    Server,
    Settings,
} from 'lucide-react';

export const FILE_TYPES = {
    component: {
        color: '#8b5cf6',
        icon: Component,
        label: 'Component',
    },
    page: {
        color: '#3b82f6',
        icon: Layout,
        label: 'Page',
    },
    store: {
        color: '#f59e0b',
        icon: Database,
        label: 'Store',
    },
    util: {
        color: '#10b981',
        icon: Code,
        label: 'Utility',
    },
    api: {
        color: '#ec4899',
        icon: Server,
        label: 'API',
    },
    config: {
        color: '#6b7280',
        icon: Settings,
        label: 'Config',
    },
    schema: {
        color: '#06b6d4',
        icon: Layers,
        label: 'Schema',
    },
    default: {
        color: '#a855f7',
        icon: FileText,
        label: 'File',
    },
} as const;

export type FileType = keyof typeof FILE_TYPES;

export function detectFileType(filePath: string): FileType {
    const path = filePath.toLowerCase();
    const fileName = path.split('/').pop() || '';

    if (path.includes('/components/') || fileName.endsWith('.component.tsx') || fileName.endsWith('.component.ts')) {
        return 'component';
    }
    if (
        path.includes('/pages/') ||
        (path.includes('/app/') && (fileName === 'page.tsx' || fileName === 'page.ts' || fileName.includes('layout')))
    ) {
        return 'page';
    }
    if (path.includes('/store') || path.includes('zustand') || path.includes('redux')) {
        return 'store';
    }
    if (path.includes('/api/') || path.includes('routes') || path.includes('service')) {
        return 'api';
    }
    if (path.includes('/utils/') || path.includes('/lib/') || path.includes('/helpers/')) {
        return 'util';
    }
    if (path.includes('config') || path.includes('.config.')) {
        return 'config';
    }
    if (path.includes('schema') || path.includes('types') || path.includes('interface')) {
        return 'schema';
    }

    return 'default';
}

export interface CustomNodeData {
    label: string;
    description?: string;
    filePath: string;
    fileType?: FileType;
    entity?: 'file' | 'module';
    moduleKey?: string;
    linesOfCode?: number;
    importance?: number;
    group?: string;
    exports?: string[];
    memberCount?: number;
    topFiles?: string[];
    dominantTypes?: string[];
    internalEdgeCount?: number;
    externalEdgeCount?: number;
    internalDensity?: number;
    lod?: 'compact' | 'full';
    metrics?: {
        in_degree: number;
        out_degree: number;
        degree: number;
        centrality: number;
    };
    isHighlighted?: boolean;
    [key: string]: unknown;
}

export type CustomFlowNode = Node<CustomNodeData, 'custom'>;

function getNodeSize(importance?: number): number {
    if (!importance) return 1;
    return 0.92 + (Math.min(10, Math.max(1, importance)) - 1) * 0.024;
}

function CustomNodeComponent({ data, selected }: NodeProps<CustomFlowNode>) {
    const fileType = data.fileType || detectFileType(data.filePath || data.label);
    const config = FILE_TYPES[fileType] || FILE_TYPES.default;
    const Icon = config.icon;

    const size = getNodeSize(data.importance);
    const degree = data.metrics?.degree ?? 0;
    const hasActivity = degree > 0;
    const isModule = data.entity === 'module';
    const lod = data.lod || 'full';

    const highlight = selected || data.isHighlighted;
    const moduleAccent = isModule ? 'border-emerald-400/45 bg-emerald-950/20' : '';

    if (lod === 'compact') {
        return (
            <div
                className={`relative min-w-[170px] cursor-pointer rounded-xl border px-3 py-2 shadow-[0_6px_16px_rgba(2,6,23,0.3)] transition-all duration-150 ${
                    highlight ? 'border-indigo-300/70 bg-zinc-900/95' : `border-zinc-700/70 bg-zinc-900/88 ${moduleAccent}`
                }`}
                style={{
                    width: `${Math.round((isModule ? 210 : 190) * size)}px`,
                }}
            >
                <Handle
                    type="target"
                    position={Position.Left}
                    className="!h-2 !w-2 !border !border-zinc-500 !bg-zinc-800"
                />
                <Handle
                    type="source"
                    position={Position.Right}
                    className="!h-2 !w-2 !border !border-zinc-500 !bg-zinc-800"
                />
                <div className="flex items-center justify-between gap-2">
                    <div className="min-w-0">
                        <p className="truncate text-xs font-semibold text-zinc-100">{data.label}</p>
                        <p className="truncate text-[10px] text-zinc-500">
                            {isModule ? `${data.memberCount || 0} files` : data.filePath.split('/').slice(0, 2).join('/')}
                        </p>
                    </div>
                    <span
                        className="inline-flex shrink-0 items-center gap-1 rounded-md border px-1 py-0.5 text-[9px] font-medium"
                        style={{ borderColor: `${config.color}66`, color: config.color, backgroundColor: `${config.color}1A` }}
                    >
                        <Icon size={9} />
                        {isModule ? 'Module' : config.label}
                    </span>
                </div>
            </div>
        );
    }

    return (
        <div
            className={`relative cursor-pointer rounded-2xl border bg-zinc-900/90 px-4 py-3 shadow-[0_8px_24px_rgba(2,6,23,0.35)] transition-all duration-150 ${
                highlight ? 'border-indigo-300/70' : `border-zinc-700/70 hover:border-zinc-500/80 ${moduleAccent}`
            }`}
            style={{
                width: `${Math.round((isModule ? 300 : 260) * size)}px`,
                boxShadow: highlight
                    ? `0 0 0 1px ${config.color}AA, 0 0 35px ${config.color}33`
                    : undefined,
            }}
        >
            <Handle
                type="target"
                position={Position.Left}
                className="!h-2.5 !w-2.5 !border !border-zinc-500 !bg-zinc-800"
            />
            <Handle
                type="source"
                position={Position.Right}
                className="!h-2.5 !w-2.5 !border !border-zinc-500 !bg-zinc-800"
            />

            <div className="mb-2 flex items-start justify-between gap-2">
                <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-zinc-100">{data.label}</p>
                    <p className="truncate text-[11px] text-zinc-400">{data.group || 'ungrouped'}</p>
                </div>
                <span
                    className="inline-flex shrink-0 items-center gap-1 rounded-md border px-1.5 py-0.5 text-[10px] font-medium"
                    style={{ borderColor: `${config.color}66`, color: config.color, backgroundColor: `${config.color}1A` }}
                >
                    <Icon size={10} />
                    {isModule ? 'Module' : config.label}
                </span>
            </div>

            <div className="grid grid-cols-3 gap-1.5 text-[10px] text-zinc-400">
                <div className="rounded-md border border-zinc-800/80 bg-zinc-950/80 px-2 py-1 text-center">
                    <div className="font-semibold text-zinc-200">{isModule ? (data.memberCount ?? 0) : (data.linesOfCode ?? 0)}</div>
                    <div>{isModule ? 'Files' : 'LOC'}</div>
                </div>
                <div className="rounded-md border border-zinc-800/80 bg-zinc-950/80 px-2 py-1 text-center">
                    <div className="font-semibold text-zinc-200">{degree}</div>
                    <div>Degree</div>
                </div>
                <div className="rounded-md border border-zinc-800/80 bg-zinc-950/80 px-2 py-1 text-center">
                    <div className="font-semibold text-zinc-200">{data.importance ?? 1}</div>
                    <div>Rank</div>
                </div>
            </div>

            <div className="mt-2 flex items-center justify-between text-[10px] text-zinc-500">
                <span className="truncate">
                    {isModule
                        ? (data.moduleKey || data.filePath || '').split('/').slice(0, 4).join('/')
                        : data.filePath.split('/').slice(0, 2).join('/') || data.filePath}
                </span>
                <span className={hasActivity ? 'text-emerald-400' : 'text-zinc-600'}>{hasActivity ? 'active' : 'idle'}</span>
            </div>
        </div>
    );
}

export const CustomNode = memo(CustomNodeComponent);
