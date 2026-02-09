'use client';

import { useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Eye, EyeOff, Filter, RotateCcw } from 'lucide-react';
import { FILE_TYPES, FileType } from './CustomNode';

const FILTER_TYPES: FileType[] = ['component', 'page', 'store', 'api', 'util', 'schema', 'config', 'default'];

interface GraphLegendProps {
    counts: Partial<Record<FileType, number>>;
    activeTypes: Set<FileType>;
    onToggleType: (type: FileType) => void;
    onReset: () => void;
    topOffset?: number;
}

export function GraphLegend({ counts, activeTypes, onToggleType, onReset, topOffset }: GraphLegendProps) {
    const [open, setOpen] = useState(true);
    const legendTop = Math.max(96, Math.round(topOffset || 120));

    const activeCount = useMemo(
        () => FILTER_TYPES.filter((type) => activeTypes.has(type)).length,
        [activeTypes]
    );
    const hiddenCount = FILTER_TYPES.length - activeCount;

    return (
        <div className="absolute left-4 z-30 w-56" style={{ top: `${legendTop}px` }}>
            <div className="overflow-hidden rounded-xl border border-zinc-800/80 bg-zinc-900/80 backdrop-blur-md">
                <button
                    type="button"
                    onClick={() => setOpen((prev) => !prev)}
                    className="flex w-full items-center justify-between px-3 py-2.5 text-left transition-colors hover:bg-zinc-800/60"
                >
                    <span className="inline-flex items-center gap-2 text-xs font-medium text-zinc-200">
                        <Filter size={13} className="text-indigo-300" />
                        Type Filters
                    </span>
                    <span className="inline-flex items-center gap-1 text-[11px] text-zinc-400">
                        {activeCount}/{FILTER_TYPES.length}
                        {hiddenCount > 0 && (
                            <span className="rounded-full bg-zinc-800 px-1.5 py-0.5 text-[10px] text-zinc-300">
                                {hiddenCount} hidden
                            </span>
                        )}
                    </span>
                </button>

                <AnimatePresence>
                    {open && (
                        <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            transition={{ duration: 0.18 }}
                            className="space-y-1 border-t border-zinc-800/70 p-2"
                        >
                            <p className="px-1 pb-1 text-[10px] text-zinc-500">
                                Toggle a type to show or hide its nodes and edges.
                            </p>
                            {FILTER_TYPES.map((type) => {
                                const config = FILE_TYPES[type];
                                const Icon = config.icon;
                                const count = counts[type] ?? 0;
                                const active = activeTypes.has(type);

                                return (
                                    <button
                                        key={type}
                                        type="button"
                                        onClick={() => onToggleType(type)}
                                        aria-pressed={active}
                                        className={`flex w-full items-center justify-between rounded-lg border px-2 py-1.5 text-xs transition-colors ${
                                            active
                                                ? 'border-zinc-700 bg-zinc-800/80 text-zinc-100'
                                                : 'border-zinc-800/80 text-zinc-400 hover:bg-zinc-800/40 hover:text-zinc-300'
                                        }`}
                                        title={active ? `Hide ${config.label}` : `Show ${config.label}`}
                                    >
                                        <span className="inline-flex items-center gap-2">
                                            <span
                                                className="grid h-5 w-5 place-items-center rounded"
                                                style={{ backgroundColor: `${config.color}22` }}
                                            >
                                                <Icon size={11} style={{ color: config.color }} />
                                            </span>
                                            {config.label}
                                        </span>
                                        <span className="inline-flex items-center gap-1.5">
                                            <span className="font-mono text-[10px] text-zinc-400">{count}</span>
                                            <span
                                                className={`inline-flex items-center gap-1 rounded-full border px-1.5 py-0.5 text-[9px] font-medium ${
                                                    active
                                                        ? 'border-emerald-500/35 bg-emerald-500/15 text-emerald-300'
                                                        : 'border-zinc-700 bg-zinc-800 text-zinc-400'
                                                }`}
                                            >
                                                {active ? <Eye size={10} /> : <EyeOff size={10} />}
                                                {active ? 'Shown' : 'Hidden'}
                                            </span>
                                        </span>
                                    </button>
                                );
                            })}

                            <button
                                type="button"
                                onClick={onReset}
                                className="mt-1 inline-flex w-full items-center justify-center gap-1.5 rounded-lg border border-zinc-700/80 px-2 py-1.5 text-[11px] text-zinc-300 transition-colors hover:bg-zinc-800/70"
                            >
                                <RotateCcw size={12} />
                                Reset: show all
                            </button>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
}
