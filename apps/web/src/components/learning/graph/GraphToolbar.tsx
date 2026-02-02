'use client';

import { motion } from 'framer-motion';
import {
    GitBranch,
    Circle,
    ArrowDownWideNarrow,
    Download,
    Loader2
} from 'lucide-react';

export type LayoutType = 'hierarchy' | 'radial' | 'vertical';

interface GraphToolbarProps {
    currentLayout: LayoutType;
    onLayoutChange: (layout: LayoutType) => void;
    onExport: () => void;
    isExporting: boolean;
    disabled?: boolean;
}

const layouts: { type: LayoutType; label: string; icon: typeof GitBranch }[] = [
    { type: 'hierarchy', label: 'Horizontal', icon: GitBranch },
    { type: 'radial', label: 'Radial', icon: Circle },
    { type: 'vertical', label: 'Vertical', icon: ArrowDownWideNarrow },
];

export function GraphToolbar({
    currentLayout,
    onLayoutChange,
    onExport,
    isExporting,
    disabled
}: GraphToolbarProps) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="absolute bottom-4 left-1/2 -translate-x-1/2 z-50 flex items-center gap-2 px-3 py-2 bg-zinc-900/95 backdrop-blur-sm border border-zinc-800 rounded-xl shadow-2xl"
        >
            {/* Layout Switcher */}
            <div className="flex items-center gap-1 pr-3 border-r border-zinc-700">
                {layouts.map(({ type, label, icon: Icon }) => (
                    <button
                        key={type}
                        onClick={() => onLayoutChange(type)}
                        disabled={disabled}
                        className={`
                            relative flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all
                            ${currentLayout === type
                                ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/25'
                                : 'text-zinc-400 hover:text-white hover:bg-zinc-800'
                            }
                            disabled:opacity-50 disabled:cursor-not-allowed
                        `}
                        title={`${label} Layout`}
                    >
                        <Icon size={14} />
                        <span className="hidden sm:inline">{label}</span>
                    </button>
                ))}
            </div>

            {/* Export Button */}
            <button
                onClick={onExport}
                disabled={disabled || isExporting}
                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium text-zinc-400 hover:text-white hover:bg-zinc-800 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                title="Export as PNG"
            >
                {isExporting ? (
                    <Loader2 size={14} className="animate-spin" />
                ) : (
                    <Download size={14} />
                )}
                <span className="hidden sm:inline">Export</span>
            </button>
        </motion.div>
    );
}
