'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { X, FileCode, ExternalLink, ArrowRight, BookOpen, Code } from 'lucide-react';
import { FILE_TYPES, FileType } from './CustomNode';

interface NodeDetailPanelProps {
    node: {
        id: string;
        data: {
            label: string;
            description?: string;
            filePath: string;
            fileType?: FileType;
            linesOfCode?: number;
        };
    } | null;
    onClose: () => void;
    incomingEdges: { source: string; label?: string }[];
    outgoingEdges: { target: string; label?: string }[];
    onNodeClick: (nodeId: string) => void;
}

export function NodeDetailPanel({
    node,
    onClose,
    incomingEdges = [],
    outgoingEdges = [],
    onNodeClick
}: NodeDetailPanelProps) {
    if (!node) return null;

    const fileType = node.data.fileType || 'default';
    const config = FILE_TYPES[fileType];
    const Icon = config.icon;

    return (
        <AnimatePresence>
            {node && (
                <>
                    {/* Backdrop */}
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={onClose}
                        className="absolute inset-0 bg-black/40 z-50"
                    />

                    {/* Panel */}
                    <motion.div
                        initial={{ x: '100%', opacity: 0 }}
                        animate={{ x: 0, opacity: 1 }}
                        exit={{ x: '100%', opacity: 0 }}
                        transition={{ type: 'spring', damping: 25, stiffness: 300 }}
                        className="absolute right-0 top-0 bottom-0 w-[400px] bg-zinc-900/95 backdrop-blur-xl border-l border-zinc-800 z-50 overflow-hidden flex flex-col"
                    >
                        {/* Header */}
                        <div className="p-4 border-b border-zinc-800">
                            <div className="flex items-start justify-between gap-3">
                                <div className="flex items-center gap-3 min-w-0">
                                    <div
                                        className="flex-shrink-0 p-2.5 rounded-xl"
                                        style={{ backgroundColor: `${config.color}20` }}
                                    >
                                        <Icon size={20} style={{ color: config.color }} />
                                    </div>
                                    <div className="min-w-0">
                                        <h3 className="text-lg font-semibold text-white truncate">
                                            {node.data.label}
                                        </h3>
                                        <span
                                            className="text-xs font-medium px-2 py-0.5 rounded-full"
                                            style={{
                                                backgroundColor: `${config.color}20`,
                                                color: config.color
                                            }}
                                        >
                                            {config.label}
                                        </span>
                                    </div>
                                </div>
                                <button
                                    onClick={onClose}
                                    className="p-2 hover:bg-zinc-800 rounded-lg transition-colors"
                                >
                                    <X size={18} className="text-zinc-400" />
                                </button>
                            </div>
                        </div>

                        {/* Content */}
                        <div className="flex-1 overflow-y-auto p-4 space-y-5">
                            {/* File Path */}
                            <div className="space-y-2">
                                <div className="flex items-center gap-2 text-xs text-zinc-500 uppercase tracking-wide">
                                    <FileCode size={12} />
                                    <span>File Path</span>
                                </div>
                                <p className="text-sm text-zinc-300 font-mono bg-zinc-800/50 px-3 py-2 rounded-lg break-all">
                                    {node.data.filePath}
                                </p>
                            </div>

                            {/* Description */}
                            {node.data.description && (
                                <div className="space-y-2">
                                    <div className="flex items-center gap-2 text-xs text-zinc-500 uppercase tracking-wide">
                                        <BookOpen size={12} />
                                        <span>Description</span>
                                    </div>
                                    <p className="text-sm text-zinc-400 leading-relaxed">
                                        {node.data.description}
                                    </p>
                                </div>
                            )}

                            {/* Stats */}
                            <div className="grid grid-cols-2 gap-3">
                                <div className="bg-zinc-800/50 rounded-xl p-3 text-center">
                                    <div className="text-2xl font-bold text-white">
                                        {incomingEdges.length}
                                    </div>
                                    <div className="text-xs text-zinc-500">Dependencies</div>
                                </div>
                                <div className="bg-zinc-800/50 rounded-xl p-3 text-center">
                                    <div className="text-2xl font-bold text-white">
                                        {outgoingEdges.length}
                                    </div>
                                    <div className="text-xs text-zinc-500">Dependents</div>
                                </div>
                            </div>

                            {/* Incoming Edges (Dependencies) */}
                            {incomingEdges.length > 0 && (
                                <div className="space-y-2">
                                    <div className="flex items-center gap-2 text-xs text-zinc-500 uppercase tracking-wide">
                                        <ArrowRight size={12} className="rotate-180" />
                                        <span>Imports From</span>
                                    </div>
                                    <div className="space-y-1">
                                        {incomingEdges.map((edge, i) => (
                                            <button
                                                key={i}
                                                onClick={() => onNodeClick(edge.source)}
                                                className="w-full text-left px-3 py-2 bg-zinc-800/50 hover:bg-zinc-800 rounded-lg text-sm text-zinc-300 hover:text-white transition-colors flex items-center justify-between group"
                                            >
                                                <span className="truncate">{edge.source.split('/').pop()}</span>
                                                <ExternalLink size={12} className="text-zinc-600 group-hover:text-indigo-400 transition-colors" />
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Outgoing Edges (Dependents) */}
                            {outgoingEdges.length > 0 && (
                                <div className="space-y-2">
                                    <div className="flex items-center gap-2 text-xs text-zinc-500 uppercase tracking-wide">
                                        <ArrowRight size={12} />
                                        <span>Imported By</span>
                                    </div>
                                    <div className="space-y-1">
                                        {outgoingEdges.map((edge, i) => (
                                            <button
                                                key={i}
                                                onClick={() => onNodeClick(edge.target)}
                                                className="w-full text-left px-3 py-2 bg-zinc-800/50 hover:bg-zinc-800 rounded-lg text-sm text-zinc-300 hover:text-white transition-colors flex items-center justify-between group"
                                            >
                                                <span className="truncate">{edge.target.split('/').pop()}</span>
                                                <ExternalLink size={12} className="text-zinc-600 group-hover:text-indigo-400 transition-colors" />
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Footer Actions */}
                        <div className="p-4 border-t border-zinc-800 space-y-2">
                            <button className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-sm font-medium transition-colors">
                                <Code size={16} />
                                View Source Code
                            </button>
                            <button className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-xl text-sm font-medium transition-colors">
                                <BookOpen size={16} />
                                Start Related Lesson
                            </button>
                        </div>
                    </motion.div>
                </>
            )}
        </AnimatePresence>
    );
}
