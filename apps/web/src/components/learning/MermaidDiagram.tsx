'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Maximize2, X, ZoomIn, ZoomOut, RotateCcw } from 'lucide-react';
import mermaid from 'mermaid';

// Initialize mermaid with dark theme
mermaid.initialize({
    startOnLoad: false,
    theme: 'dark',
    themeVariables: {
        primaryColor: '#6366f1',
        primaryTextColor: '#e4e4e7',
        primaryBorderColor: '#4f46e5',
        lineColor: '#6366f1',
        secondaryColor: '#27272a',
        tertiaryColor: '#18181b',
        background: '#09090b',
        mainBkg: '#18181b',
        nodeBorder: '#4f46e5',
        clusterBkg: '#27272a',
        titleColor: '#e4e4e7',
        edgeLabelBackground: '#27272a',
    },
    flowchart: {
        htmlLabels: true,
        curve: 'basis',
        padding: 20,
    },
    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
});

interface MermaidDiagramProps {
    code: string;
    className?: string;
}

/**
 * Sanitize Mermaid code to fix common LLM-generated syntax issues
 * - Wraps node labels containing special characters in quotes
 * - Escapes parentheses in labels
 */
function sanitizeMermaidCode(code: string): string {
    // Replace node labels with parentheses: A[Label (Info)] -> A["Label (Info)"]
    let sanitized = code.replace(
        /(\w+)\[([^\]]*\([^\]]*\)[^\]]*)\]/g,
        (match, id, label) => `${id}["${label.replace(/"/g, "'")}"]`
    );

    // Also handle curly braces in labels
    sanitized = sanitized.replace(
        /(\w+)\[([^\]]*\{[^\]]*\}[^\]]*)\]/g,
        (match, id, label) => `${id}["${label.replace(/"/g, "'")}"]`
    );

    return sanitized;
}

export function MermaidDiagram({ code, className = '' }: MermaidDiagramProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const [svg, setSvg] = useState<string>('');
    const [isFullscreen, setIsFullscreen] = useState(false);
    const [zoom, setZoom] = useState(1);
    const [error, setError] = useState<string | null>(null);
    const [isRendering, setIsRendering] = useState(true);

    const renderDiagram = useCallback(async () => {
        if (!code) return;

        setIsRendering(true);
        setError(null);

        try {
            // Generate unique ID for this render
            const id = `mermaid-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;

            // Sanitize the code to fix common LLM issues
            const sanitizedCode = sanitizeMermaidCode(code);

            // Render the diagram
            const { svg: renderedSvg } = await mermaid.render(id, sanitizedCode);
            setSvg(renderedSvg);
        } catch (err) {
            console.error('Mermaid render error:', err);
            setError(err instanceof Error ? err.message : 'Failed to render diagram');
        } finally {
            setIsRendering(false);
        }
    }, [code]);

    useEffect(() => {
        renderDiagram();
    }, [renderDiagram]);

    const handleZoomIn = () => setZoom((z) => Math.min(z + 0.25, 3));
    const handleZoomOut = () => setZoom((z) => Math.max(z - 0.25, 0.5));
    const handleResetZoom = () => setZoom(1);

    if (error) {
        return (
            <div className={`p-6 bg-red-950/30 border border-red-900/50 rounded-xl ${className}`}>
                <p className="text-red-400 text-sm font-medium mb-2">Failed to render diagram</p>
                <pre className="text-xs text-red-300/70 overflow-x-auto">{code}</pre>
            </div>
        );
    }

    if (isRendering) {
        return (
            <div className={`p-8 bg-zinc-900/50 border border-zinc-800 rounded-xl flex items-center justify-center ${className}`}>
                <div className="flex items-center gap-3 text-zinc-500">
                    <div className="w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                    <span className="text-sm">Rendering diagram...</span>
                </div>
            </div>
        );
    }

    return (
        <>
            {/* Inline Diagram */}
            <div className={`relative group ${className}`}>
                <div className="bg-zinc-900/80 border border-zinc-800 rounded-xl overflow-hidden">
                    {/* Header */}
                    <div className="flex items-center justify-between px-4 py-2 border-b border-zinc-800 bg-zinc-900/50">
                        <span className="text-xs font-medium text-zinc-500 uppercase tracking-wider">
                            Architecture Diagram
                        </span>
                        <div className="flex items-center gap-1">
                            <button
                                onClick={handleZoomOut}
                                className="p-1.5 hover:bg-zinc-800 rounded text-zinc-500 hover:text-white transition-colors"
                                title="Zoom Out"
                            >
                                <ZoomOut size={14} />
                            </button>
                            <span className="text-xs text-zinc-600 min-w-[40px] text-center">{Math.round(zoom * 100)}%</span>
                            <button
                                onClick={handleZoomIn}
                                className="p-1.5 hover:bg-zinc-800 rounded text-zinc-500 hover:text-white transition-colors"
                                title="Zoom In"
                            >
                                <ZoomIn size={14} />
                            </button>
                            <button
                                onClick={handleResetZoom}
                                className="p-1.5 hover:bg-zinc-800 rounded text-zinc-500 hover:text-white transition-colors"
                                title="Reset Zoom"
                            >
                                <RotateCcw size={14} />
                            </button>
                            <div className="w-px h-4 bg-zinc-800 mx-1" />
                            <button
                                onClick={() => setIsFullscreen(true)}
                                className="p-1.5 hover:bg-zinc-800 rounded text-zinc-500 hover:text-white transition-colors"
                                title="Fullscreen"
                            >
                                <Maximize2 size={14} />
                            </button>
                        </div>
                    </div>

                    {/* Diagram Container */}
                    <div
                        ref={containerRef}
                        className="p-6 overflow-auto max-h-[400px] flex items-center justify-center"
                    >
                        <div
                            style={{ transform: `scale(${zoom})`, transformOrigin: 'center center' }}
                            className="transition-transform duration-200"
                            dangerouslySetInnerHTML={{ __html: svg }}
                        />
                    </div>
                </div>
            </div>

            {/* Fullscreen Modal */}
            <AnimatePresence>
                {isFullscreen && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        className="fixed inset-0 z-[100] bg-zinc-950/95 backdrop-blur-sm flex flex-col"
                    >
                        {/* Fullscreen Header */}
                        <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800">
                            <span className="text-sm font-medium text-white">Architecture Diagram</span>
                            <div className="flex items-center gap-2">
                                <button
                                    onClick={handleZoomOut}
                                    className="p-2 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-white transition-colors"
                                >
                                    <ZoomOut size={18} />
                                </button>
                                <span className="text-sm text-zinc-500 min-w-[50px] text-center">{Math.round(zoom * 100)}%</span>
                                <button
                                    onClick={handleZoomIn}
                                    className="p-2 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-white transition-colors"
                                >
                                    <ZoomIn size={18} />
                                </button>
                                <button
                                    onClick={handleResetZoom}
                                    className="p-2 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-white transition-colors"
                                >
                                    <RotateCcw size={18} />
                                </button>
                                <div className="w-px h-6 bg-zinc-800 mx-2" />
                                <button
                                    onClick={() => setIsFullscreen(false)}
                                    className="p-2 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-white transition-colors"
                                >
                                    <X size={18} />
                                </button>
                            </div>
                        </div>

                        {/* Fullscreen Diagram */}
                        <div className="flex-1 overflow-auto flex items-center justify-center p-8">
                            <div
                                style={{ transform: `scale(${zoom})`, transformOrigin: 'center center' }}
                                className="transition-transform duration-200"
                                dangerouslySetInnerHTML={{ __html: svg }}
                            />
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </>
    );
}
