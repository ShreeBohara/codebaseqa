'use client';

import { useEffect, useMemo, useState } from 'react';
import { ExternalLink, Network, PanelRightClose, PanelRightOpen } from 'lucide-react';
import { api } from '@/lib/api-client';
import { FILE_TYPES, FileType } from './CustomNode';

interface GraphNodeShape {
    id: string;
    data: {
        label: string;
        description?: string;
        filePath: string;
        fileType?: FileType;
        entity?: 'file' | 'module';
        moduleKey?: string;
        linesOfCode?: number;
        exports?: string[];
        memberCount?: number;
        topFiles?: string[];
        dominantTypes?: string[];
        internalEdgeCount?: number;
        externalEdgeCount?: number;
        internalDensity?: number;
        metrics?: {
            in_degree: number;
            out_degree: number;
            degree: number;
            centrality: number;
        };
    };
}

interface NodeDetailPanelProps {
    repoId: string;
    node: GraphNodeShape | null;
    incomingEdges: { source: string; label?: string }[];
    outgoingEdges: { target: string; label?: string }[];
    onNodeClick: (nodeId: string) => void;
    onDrillDownModule?: (moduleKey: string) => void;
    open: boolean;
    onToggleOpen: () => void;
}

export function NodeDetailPanel({
    repoId,
    node,
    incomingEdges,
    outgoingEdges,
    onNodeClick,
    onDrillDownModule,
    open,
    onToggleOpen,
}: NodeDetailPanelProps) {
    const [sourceCode, setSourceCode] = useState('');
    const [sourceLoading, setSourceLoading] = useState(false);
    const [sourceError, setSourceError] = useState<string | null>(null);
    const [expandedSource, setExpandedSource] = useState(false);
    const nodeId = node?.id || null;
    const filePath = node?.data.filePath || '';
    const isModule = node?.data.entity === 'module';
    const moduleKey = node?.data.moduleKey || '';

    const fileType = node?.data.fileType || 'default';
    const config = FILE_TYPES[fileType];
    const Icon = config.icon;

    useEffect(() => {
        let cancelled = false;

        async function loadSource() {
            if (!nodeId || !filePath || isModule) {
                setSourceCode('');
                setSourceError(null);
                return;
            }

            setSourceLoading(true);
            setSourceError(null);
            setExpandedSource(false);

            try {
                const res = await api.getRepoFileContent(repoId, filePath);
                if (!cancelled) {
                    setSourceCode(res.content || '');
                }
            } catch {
                if (!cancelled) {
                    setSourceError('Unable to load source preview.');
                    setSourceCode('');
                }
            } finally {
                if (!cancelled) {
                    setSourceLoading(false);
                }
            }
        }

        loadSource();
        return () => {
            cancelled = true;
        };
    }, [filePath, isModule, nodeId, repoId]);

    const previewCode = useMemo(() => {
        if (!sourceCode) return '';
        if (expandedSource) return sourceCode;
        return sourceCode.split('\n').slice(0, 80).join('\n');
    }, [sourceCode, expandedSource]);

    return (
        <aside
            className={`
                relative transition-all duration-200
                ${open
                    ? 'w-full border-l border-zinc-800/80 bg-zinc-950/90 backdrop-blur-md md:w-[360px] xl:w-[390px]'
                    : 'w-12 border-l border-zinc-800/60 bg-zinc-950/70 backdrop-blur-sm'}
            `}
        >
            <button
                type="button"
                onClick={onToggleOpen}
                className="absolute left-2 top-2 z-20 inline-flex h-8 w-8 items-center justify-center rounded-md border border-zinc-800 bg-zinc-900/80 text-zinc-300 transition-colors hover:bg-zinc-800"
                title={open ? 'Collapse inspector' : 'Expand inspector'}
            >
                {open ? <PanelRightClose size={14} /> : <PanelRightOpen size={14} />}
            </button>

            {!open ? null : !node ? (
                <div className="flex h-full items-center justify-center px-6 text-center">
                    <div>
                        <Network className="mx-auto mb-3 text-zinc-600" size={24} />
                        <p className="text-sm text-zinc-400">Select a node to inspect dependencies and source preview.</p>
                    </div>
                </div>
            ) : (
                <div className="flex h-full flex-col overflow-hidden">
                    <div className="border-b border-zinc-800/80 px-4 pb-4 pt-12">
                        <div className="mb-2 flex items-start justify-between gap-2">
                            <div className="min-w-0">
                                <h3 className="truncate text-base font-semibold text-zinc-100">{node.data.label}</h3>
                                <p className="truncate text-xs text-zinc-400">{node.data.filePath}</p>
                            </div>
                            <span
                                className="inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-[10px] font-medium"
                                style={{ borderColor: `${config.color}66`, color: config.color, backgroundColor: `${config.color}1A` }}
                            >
                                <Icon size={10} />
                                {config.label}
                            </span>
                        </div>
                        <p className="text-xs leading-relaxed text-zinc-400">{node.data.description || 'No description available.'}</p>
                    </div>

                    <div className="flex-1 space-y-5 overflow-y-auto px-4 py-4">
                        <div className="grid grid-cols-2 gap-2 text-[11px]">
                            <StatCard label={isModule ? 'Files' : 'LOC'} value={String(isModule ? (node.data.memberCount || 0) : (node.data.linesOfCode || 0))} />
                            <StatCard label="Degree" value={String(node.data.metrics?.degree || 0)} />
                            <StatCard label="In" value={String(node.data.metrics?.in_degree || 0)} />
                            <StatCard label="Out" value={String(node.data.metrics?.out_degree || 0)} />
                            {isModule && (
                                <>
                                    <StatCard label="Internal" value={String(node.data.internalEdgeCount || 0)} />
                                    <StatCard label="External" value={String(node.data.externalEdgeCount || 0)} />
                                    <StatCard label="Int. Density" value={String((node.data.internalDensity || 0).toFixed(3))} />
                                </>
                            )}
                        </div>

                        {isModule && (
                            <section className="space-y-2">
                                <div className="flex items-center justify-between">
                                    <h4 className="text-xs font-medium uppercase tracking-wider text-zinc-500">Module Scope</h4>
                                    {!!moduleKey && onDrillDownModule && (
                                        <button
                                            type="button"
                                            onClick={() => onDrillDownModule(moduleKey)}
                                            className="rounded-md border border-emerald-700/70 bg-emerald-500/10 px-2 py-0.5 text-[10px] text-emerald-300 hover:bg-emerald-500/20"
                                        >
                                            Open File Graph
                                        </button>
                                    )}
                                </div>
                                {node.data.moduleKey && (
                                    <p className="truncate rounded-md border border-zinc-800 bg-zinc-900/70 px-2 py-1 text-[11px] text-zinc-300">
                                        {node.data.moduleKey}
                                    </p>
                                )}
                                {!!node.data.dominantTypes?.length && (
                                    <div className="flex flex-wrap gap-1.5">
                                        {node.data.dominantTypes.map((type) => (
                                            <span key={type} className="rounded-md border border-zinc-700 bg-zinc-900 px-2 py-0.5 text-[10px] text-zinc-300">
                                                {type}
                                            </span>
                                        ))}
                                    </div>
                                )}
                            </section>
                        )}

                        {isModule && !!node.data.topFiles?.length && (
                            <section>
                                <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-zinc-500">Top Files</h4>
                                <div className="space-y-1.5">
                                    {node.data.topFiles.slice(0, 8).map((item) => (
                                        <div
                                            key={item}
                                            className="truncate rounded-md border border-zinc-800 bg-zinc-900/70 px-2.5 py-1.5 text-[11px] text-zinc-300"
                                        >
                                            {item}
                                        </div>
                                    ))}
                                </div>
                            </section>
                        )}

                        {!!node.data.exports?.length && (
                            <section>
                                <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-zinc-500">Exports</h4>
                                <div className="flex flex-wrap gap-1.5">
                                    {node.data.exports.slice(0, 12).map((item) => (
                                        <span key={item} className="rounded-md border border-zinc-700 bg-zinc-900 px-2 py-0.5 text-[10px] text-zinc-300">
                                            {item}
                                        </span>
                                    ))}
                                </div>
                            </section>
                        )}

                        <RelationList
                            title="Imported By"
                            items={incomingEdges.map((edge) => ({ id: edge.source, label: edge.label }))}
                            onNodeClick={onNodeClick}
                        />
                        <RelationList
                            title="Imports From"
                            items={outgoingEdges.map((edge) => ({ id: edge.target, label: edge.label }))}
                            onNodeClick={onNodeClick}
                        />

                        {!isModule && (
                            <section>
                                <div className="mb-2 flex items-center justify-between">
                                    <h4 className="text-xs font-medium uppercase tracking-wider text-zinc-500">Source Preview</h4>
                                    <button
                                        type="button"
                                        onClick={() => setExpandedSource((prev) => !prev)}
                                        disabled={!sourceCode || sourceLoading}
                                        className="rounded-md border border-zinc-700 px-2 py-0.5 text-[10px] text-zinc-300 transition-colors hover:bg-zinc-800 disabled:opacity-40"
                                    >
                                        {expandedSource ? 'Show Less' : 'View Source Code'}
                                    </button>
                                </div>

                                <div className="overflow-hidden rounded-lg border border-zinc-800 bg-zinc-950">
                                    {sourceLoading ? (
                                        <div className="p-3 text-xs text-zinc-500">Loading source...</div>
                                    ) : sourceError ? (
                                        <div className="p-3 text-xs text-rose-400">{sourceError}</div>
                                    ) : previewCode ? (
                                        <pre className="max-h-[300px] overflow-auto p-3 text-[11px] leading-relaxed text-zinc-300">
                                            {previewCode}
                                        </pre>
                                    ) : (
                                        <div className="p-3 text-xs text-zinc-500">No source preview available.</div>
                                    )}
                                </div>
                            </section>
                        )}
                    </div>
                </div>
            )}
        </aside>
    );
}

function StatCard({ label, value }: { label: string; value: string }) {
    return (
        <div className="rounded-lg border border-zinc-800 bg-zinc-900/70 px-2 py-2 text-center">
            <div className="text-sm font-semibold text-zinc-200">{value}</div>
            <div className="text-[10px] uppercase tracking-wider text-zinc-500">{label}</div>
        </div>
    );
}

function RelationList({
    title,
    items,
    onNodeClick,
}: {
    title: string;
    items: Array<{ id: string; label?: string }>;
    onNodeClick: (nodeId: string) => void;
}) {
    if (items.length === 0) {
        return null;
    }

    return (
        <section>
            <h4 className="mb-2 text-xs font-medium uppercase tracking-wider text-zinc-500">{title}</h4>
            <div className="space-y-1.5">
                {items.slice(0, 12).map((item) => (
                    <button
                        key={`${title}-${item.id}`}
                        type="button"
                        onClick={() => onNodeClick(item.id)}
                        className="flex w-full items-center justify-between rounded-md border border-zinc-800 bg-zinc-900/70 px-2.5 py-1.5 text-left text-[11px] text-zinc-300 transition-colors hover:border-zinc-700 hover:bg-zinc-800"
                    >
                        <span className="min-w-0 truncate">{item.id.split('/').pop()}</span>
                        <span className="ml-2 inline-flex items-center gap-1 text-[10px] text-zinc-500">
                            {item.label || 'imports'}
                            <ExternalLink size={10} />
                        </span>
                    </button>
                ))}
            </div>
        </section>
    );
}
