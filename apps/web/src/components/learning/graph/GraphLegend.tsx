'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { FILE_TYPES, FileType } from './CustomNode';

export function GraphLegend() {
    const [isOpen, setIsOpen] = useState(true);

    const types: FileType[] = ['component', 'page', 'store', 'api', 'util', 'schema', 'config'];

    return (
        <div className="absolute bottom-4 left-4 z-50">
            <motion.div
                layout
                className="bg-zinc-900/95 backdrop-blur-sm border border-zinc-800 rounded-xl overflow-hidden shadow-xl"
            >
                {/* Header */}
                <button
                    onClick={() => setIsOpen(!isOpen)}
                    className="w-full px-4 py-2.5 flex items-center justify-between gap-3 hover:bg-zinc-800/50 transition-colors"
                >
                    <span className="text-xs font-medium text-zinc-400">Legend</span>
                    {isOpen ? (
                        <ChevronDown size={14} className="text-zinc-500" />
                    ) : (
                        <ChevronUp size={14} className="text-zinc-500" />
                    )}
                </button>

                {/* Content */}
                <AnimatePresence>
                    {isOpen && (
                        <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            transition={{ duration: 0.2 }}
                            className="px-4 pb-3"
                        >
                            <div className="space-y-2">
                                {types.map((type) => {
                                    const config = FILE_TYPES[type];
                                    const Icon = config.icon;
                                    return (
                                        <div key={type} className="flex items-center gap-2.5">
                                            <div
                                                className="w-5 h-5 rounded flex items-center justify-center"
                                                style={{ backgroundColor: `${config.color}25` }}
                                            >
                                                <Icon size={12} style={{ color: config.color }} />
                                            </div>
                                            <span className="text-xs text-zinc-400">
                                                {config.label}
                                            </span>
                                        </div>
                                    );
                                })}
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </motion.div>
        </div>
    );
}
