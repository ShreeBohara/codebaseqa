'use client';

import { motion } from 'framer-motion';
import {
    Compass,
    Download,
    Ellipsis,
    Focus,
    Loader2,
    Map,
    RefreshCw,
} from 'lucide-react';

interface GraphToolbarProps {
    onFit: () => void;
    onCenter: () => void;
    onRegenerate: () => void;
    onExport: () => void;
    onToggleMiniMap: () => void;
    miniMapVisible: boolean;
    isExporting: boolean;
    isLoading?: boolean;
    disabled?: boolean;
}

export function GraphToolbar({
    onFit,
    onCenter,
    onRegenerate,
    onExport,
    onToggleMiniMap,
    miniMapVisible,
    isExporting,
    isLoading,
    disabled,
}: GraphToolbarProps) {
    return (
        <motion.div
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            className="inline-flex items-center gap-2 rounded-xl border border-zinc-800/80 bg-zinc-900/80 px-2 py-2 backdrop-blur-md"
        >
            <div className="inline-flex items-center rounded-lg border border-zinc-700/80 bg-zinc-900/70 p-1">
                <button
                    type="button"
                    onClick={onFit}
                    disabled={disabled}
                    className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium text-zinc-300 transition-colors hover:bg-zinc-800/80 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
                    title="Fit graph in viewport"
                >
                    <Focus size={14} />
                    <span>Fit</span>
                </button>

                <button
                    type="button"
                    onClick={onCenter}
                    disabled={disabled}
                    className="inline-flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium text-zinc-300 transition-colors hover:bg-zinc-800/80 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
                    title="Center selected node"
                >
                    <Compass size={14} />
                    <span>Center</span>
                </button>
            </div>

            <button
                type="button"
                onClick={onRegenerate}
                disabled={disabled || isLoading}
                className="inline-flex items-center gap-1.5 rounded-lg border border-zinc-700/80 bg-zinc-900/70 px-2.5 py-2 text-xs font-medium text-zinc-300 transition-colors hover:bg-zinc-800/80 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
                title="Regenerate graph"
            >
                {isLoading ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                <span>Regenerate</span>
            </button>

            <details className="relative">
                <summary className="inline-flex list-none cursor-pointer items-center gap-1.5 rounded-lg border border-zinc-700/80 bg-zinc-900/70 px-2.5 py-2 text-xs font-medium text-zinc-300 transition-colors hover:bg-zinc-800/80 hover:text-white [&::-webkit-details-marker]:hidden">
                    <Ellipsis size={14} />
                    <span>More</span>
                </summary>
                <div className="absolute right-0 top-10 z-50 min-w-[150px] rounded-lg border border-zinc-700/90 bg-zinc-900/95 p-1 shadow-xl backdrop-blur-md">
                    <button
                        type="button"
                        onClick={onToggleMiniMap}
                        aria-pressed={miniMapVisible}
                        className="flex w-full items-center justify-between rounded-md px-2.5 py-2 text-xs font-medium text-zinc-300 transition-colors hover:bg-zinc-800/80 hover:text-white"
                        title="Toggle minimap"
                    >
                        <span className="inline-flex items-center gap-2">
                            <Map size={14} />
                            <span>Mini Map</span>
                        </span>
                        <span
                            className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${
                                miniMapVisible
                                    ? 'border-emerald-500/40 bg-emerald-500/20 text-emerald-300'
                                    : 'border-zinc-600 bg-zinc-800 text-zinc-300'
                            }`}
                        >
                            {miniMapVisible ? 'On' : 'Off'}
                        </span>
                    </button>
                    <button
                        type="button"
                        onClick={onExport}
                        disabled={disabled || isExporting}
                        className="mt-1 flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-xs font-medium text-zinc-300 transition-colors hover:bg-zinc-800/80 hover:text-white disabled:cursor-not-allowed disabled:opacity-50"
                        title="Export PNG"
                    >
                        {isExporting ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />}
                        <span>Export PNG</span>
                    </button>
                </div>
            </details>
        </motion.div>
    );
}
