'use client';

import { useEffect, useRef, useState, useCallback, useMemo, type PointerEvent } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Hand, Maximize2, X, ZoomIn, ZoomOut, RotateCcw } from 'lucide-react';
import mermaid from 'mermaid';

// Initialize mermaid with dark theme
mermaid.initialize({
    startOnLoad: false,
    theme: 'dark',
    themeVariables: {
        primaryColor: '#1f2937',
        primaryTextColor: '#e5e7eb',
        primaryBorderColor: '#38bdf8',
        lineColor: '#38bdf8',
        secondaryColor: '#111827',
        tertiaryColor: '#0b1220',
        background: '#09090b',
        mainBkg: '#111827',
        nodeBorder: '#38bdf8',
        clusterBkg: '#111827',
        titleColor: '#e5e7eb',
        edgeLabelBackground: '#0f172a',
    },
    flowchart: {
        htmlLabels: true,
        curve: 'linear',
        padding: 26,
        nodeSpacing: 45,
        rankSpacing: 60,
        useMaxWidth: false,
    },
    fontFamily: 'ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif',
});

interface MermaidDiagramProps {
    code: string;
    className?: string;
}

interface DiagramDimensions {
    width: number;
    height: number;
}

interface DiagramBounds extends DiagramDimensions {
    x: number;
    y: number;
}

function normalizeRenderedSvg(svgMarkup: string): { svg: string; dimensions: DiagramDimensions } {
    try {
        const parser = new DOMParser();
        const doc = parser.parseFromString(svgMarkup, 'image/svg+xml');
        const svgEl = doc.documentElement;

        if (!svgEl || svgEl.nodeName.toLowerCase() !== 'svg') {
            return { svg: svgMarkup, dimensions: { width: 1400, height: 900 } };
        }

        let width = 0;
        let height = 0;
        const viewBox = svgEl.getAttribute('viewBox');
        if (viewBox) {
            const parts = viewBox.split(/[\s,]+/).map((token) => Number(token));
            if (parts.length === 4 && Number.isFinite(parts[2]) && Number.isFinite(parts[3])) {
                width = parts[2];
                height = parts[3];
            }
        }

        if (!width || !height) {
            const rawWidth = Number((svgEl.getAttribute('width') || '').replace(/[^0-9.]/g, ''));
            const rawHeight = Number((svgEl.getAttribute('height') || '').replace(/[^0-9.]/g, ''));
            width = Number.isFinite(rawWidth) && rawWidth > 0 ? rawWidth : 1400;
            height = Number.isFinite(rawHeight) && rawHeight > 0 ? rawHeight : 900;
        }

        svgEl.setAttribute('width', `${Math.round(width)}`);
        svgEl.setAttribute('height', `${Math.round(height)}`);
        svgEl.setAttribute('preserveAspectRatio', 'xMinYMin meet');

        const cleanedStyle = (svgEl.getAttribute('style') || '')
            .replace(/max-width\s*:\s*[^;]+;?/gi, '')
            .trim();
        svgEl.setAttribute('style', [cleanedStyle, 'display:block'].filter(Boolean).join('; '));

        const styleTag = doc.createElementNS('http://www.w3.org/2000/svg', 'style');
        styleTag.textContent = `
          .nodeLabel { font-size: 18px !important; }
          .edgeLabel { font-size: 16px !important; }
          .edgeLabel p { line-height: 1.35 !important; }
          .node rect, .node polygon, .node path { stroke-width: 1.4px !important; }
          .edgePath path { stroke-width: 1.6px !important; }
        `;
        svgEl.appendChild(styleTag);

        return {
            svg: new XMLSerializer().serializeToString(svgEl),
            dimensions: {
                width: Math.max(300, width),
                height: Math.max(220, height),
            },
        };
    } catch {
        return { svg: svgMarkup, dimensions: { width: 1400, height: 900 } };
    }
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

function isGeneratedStructuralMap(code: string): boolean {
    return (
        code.includes('subgraph CODE[Referenced Code Files]') ||
        code.includes('subgraph CODE["Referenced Code Files"]') ||
        code.includes('Persona Lens:')
    );
}

function getDiagramStats(code: string): { nodes: number; edges: number } {
    const nodeIds = new Set<string>();
    const nodeMatches = code.matchAll(/\b([A-Za-z][A-Za-z0-9_]*)\s*\[/g);
    for (const match of nodeMatches) {
        nodeIds.add(match[1]);
    }
    const edges = (code.match(/-->|==>|---/g) || []).length;
    return { nodes: nodeIds.size, edges };
}

export function MermaidDiagram({ code, className = '' }: MermaidDiagramProps) {
    const containerRef = useRef<HTMLDivElement>(null);
    const fullscreenCanvasRef = useRef<HTMLDivElement>(null);
    const panStateRef = useRef<{ startX: number; startY: number; scrollLeft: number; scrollTop: number } | null>(null);
    const [svg, setSvg] = useState<string>('');
    const [isFullscreen, setIsFullscreen] = useState(false);
    const [zoom, setZoom] = useState(1);
    const [error, setError] = useState<string | null>(null);
    const [isRendering, setIsRendering] = useState(true);
    const [isPanning, setIsPanning] = useState(false);
    const [inlineScale, setInlineScale] = useState(1);
    const [svgDimensions, setSvgDimensions] = useState<DiagramDimensions>({ width: 1400, height: 900 });
    const [contentBounds, setContentBounds] = useState<DiagramBounds>({ x: 0, y: 0, width: 1400, height: 900 });
    const stats = useMemo(() => getDiagramStats(code), [code]);
    const zoomPercent = Math.round(zoom * 100);
    const baseWidth = Math.max(280, Math.round(contentBounds.width));
    const baseHeight = Math.max(220, Math.round(contentBounds.height));
    const inlineWidth = Math.max(280, Math.round(baseWidth * inlineScale));
    const inlineHeight = Math.max(220, Math.round(baseHeight * inlineScale));
    const scaledWidth = Math.max(280, Math.round(baseWidth * zoom));
    const scaledHeight = Math.max(220, Math.round(baseHeight * zoom));

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
            const normalized = normalizeRenderedSvg(renderedSvg);
            setSvg(normalized.svg);
            setSvgDimensions(normalized.dimensions);
            setContentBounds({
                x: 0,
                y: 0,
                width: normalized.dimensions.width,
                height: normalized.dimensions.height,
            });
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

    const handleZoomIn = () => setZoom((z) => Math.min(z + 0.25, 8));
    const handleZoomOut = () => setZoom((z) => Math.max(z - 0.25, 0.4));
    const handleResetZoom = () => setZoom(1);
    const centerFullscreenCanvas = useCallback((behavior: ScrollBehavior = 'auto') => {
        const canvas = fullscreenCanvasRef.current;
        if (!canvas) return;
        const left = Math.max(0, (canvas.scrollWidth - canvas.clientWidth) / 2);
        const top = Math.max(0, (canvas.scrollHeight - canvas.clientHeight) / 2);
        canvas.scrollTo({ left, top, behavior });
    }, []);
    const handleFitZoom = useCallback(() => {
        const canvas = fullscreenCanvasRef.current;
        if (!canvas) return;
        const fitWidth = (canvas.clientWidth - 56) / baseWidth;
        const fitHeight = (canvas.clientHeight - 56) / baseHeight;
        const target = Math.max(0.4, Math.min(8, Math.min(fitWidth, fitHeight) * 0.94));
        setZoom(target);
        requestAnimationFrame(() => centerFullscreenCanvas('smooth'));
    }, [baseHeight, baseWidth, centerFullscreenCanvas]);
    const updateInlineScale = useCallback(() => {
        const container = containerRef.current;
        if (!container) return;
        const availableWidth = Math.max(280, container.clientWidth - 40);
        const nextScale = Math.min(1, availableWidth / Math.max(1, baseWidth));
        setInlineScale(nextScale);
    }, [baseWidth]);
    const handleOpenFullscreen = () => {
        setZoom(1.1);
        setIsFullscreen(true);
    };
    const handleCloseFullscreen = () => {
        setZoom(1);
        setIsFullscreen(false);
    };

    useEffect(() => {
        if (!isFullscreen) return;
        const frame = window.requestAnimationFrame(() => {
            handleFitZoom();
        });
        return () => window.cancelAnimationFrame(frame);
    }, [isFullscreen, handleFitZoom]);

    useEffect(() => {
        if (isFullscreen) {
            const frame = window.requestAnimationFrame(() => {
                centerFullscreenCanvas();
            });
            return () => window.cancelAnimationFrame(frame);
        }
        return undefined;
    }, [centerFullscreenCanvas, isFullscreen, scaledHeight, scaledWidth]);

    useEffect(() => {
        updateInlineScale();
        const container = containerRef.current;
        if (!container || typeof ResizeObserver === 'undefined') return undefined;
        const observer = new ResizeObserver(() => {
            updateInlineScale();
        });
        observer.observe(container);
        return () => observer.disconnect();
    }, [updateInlineScale]);

    useEffect(() => {
        const host = isFullscreen ? fullscreenCanvasRef.current : containerRef.current;
        if (!host) return;
        const frame = window.requestAnimationFrame(() => {
            try {
                const svgEl = host.querySelector('svg') as SVGSVGElement | null;
                if (!svgEl) return;
                const rootGroup = (svgEl.querySelector('g.output') as SVGGElement | null)
                    || (svgEl.querySelector('g') as SVGGElement | null)
                    || svgEl;
                const bbox = rootGroup.getBBox();
                if (!Number.isFinite(bbox.width) || !Number.isFinite(bbox.height) || bbox.width <= 0 || bbox.height <= 0) {
                    return;
                }
                setContentBounds({
                    x: bbox.x,
                    y: bbox.y,
                    width: bbox.width,
                    height: bbox.height,
                });
            } catch {
                // Keep previous bounds if browser cannot compute getBBox for this frame.
            }
        });
        return () => window.cancelAnimationFrame(frame);
    }, [isFullscreen, svg, zoom]);

    const stopPanning = useCallback(() => {
        panStateRef.current = null;
        setIsPanning(false);
    }, []);

    const handleCanvasPointerDown = (event: PointerEvent<HTMLDivElement>) => {
        if (event.button !== 0) return;
        const canvas = fullscreenCanvasRef.current;
        if (!canvas) return;
        panStateRef.current = {
            startX: event.clientX,
            startY: event.clientY,
            scrollLeft: canvas.scrollLeft,
            scrollTop: canvas.scrollTop,
        };
        setIsPanning(true);
        event.currentTarget.setPointerCapture(event.pointerId);
    };

    const handleCanvasPointerMove = (event: PointerEvent<HTMLDivElement>) => {
        const canvas = fullscreenCanvasRef.current;
        const panState = panStateRef.current;
        if (!canvas || !panState) return;
        event.preventDefault();
        const deltaX = event.clientX - panState.startX;
        const deltaY = event.clientY - panState.startY;
        canvas.scrollLeft = panState.scrollLeft - deltaX;
        canvas.scrollTop = panState.scrollTop - deltaY;
    };

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
                        <div className="flex min-w-0 items-center gap-2">
                            <span className="text-xs font-medium text-zinc-500 uppercase tracking-wider">
                                System Flow Map
                            </span>
                            {isGeneratedStructuralMap(code) && (
                                <span className="rounded-full border border-zinc-700 bg-zinc-900 px-2 py-0.5 text-[10px] uppercase tracking-wider text-zinc-400">
                                    Auto Structured
                                </span>
                            )}
                            <span className="text-[11px] text-zinc-600">
                                {stats.nodes} nodes / {stats.edges} links
                            </span>
                        </div>
                        <div className="flex items-center gap-1">
                            <button
                                onClick={handleOpenFullscreen}
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
                        className="max-h-[430px] overflow-auto bg-[radial-gradient(circle_at_top,rgba(56,189,248,0.08),transparent_55%)] p-6"
                    >
                        <div
                            className="relative mx-auto"
                            style={{
                                width: inlineWidth,
                                height: inlineHeight,
                            }}
                        >
                            <div
                                style={{
                                    width: baseWidth,
                                    height: baseHeight,
                                    transform: `scale(${inlineScale})`,
                                    transformOrigin: 'top left',
                                }}
                                className="[&_svg_text]:text-[13px]"
                            >
                                <div
                                    style={{
                                        width: svgDimensions.width,
                                        height: svgDimensions.height,
                                        transform: `translate(${-contentBounds.x}px, ${-contentBounds.y}px)`,
                                        transformOrigin: 'top left',
                                    }}
                                    dangerouslySetInnerHTML={{ __html: svg }}
                                />
                            </div>
                        </div>
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
                            <span className="text-sm font-medium text-white">System Flow Map</span>
                            <div className="flex items-center gap-2">
                                <button
                                    onClick={handleZoomOut}
                                    className="p-2 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-white transition-colors"
                                >
                                    <ZoomOut size={18} />
                                </button>
                                <span className="text-sm text-zinc-500 min-w-[50px] text-center">{zoomPercent}%</span>
                                <button
                                    onClick={handleZoomIn}
                                    className="p-2 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-white transition-colors"
                                >
                                    <ZoomIn size={18} />
                                </button>
                                <button
                                    onClick={handleFitZoom}
                                    className="rounded-lg px-2 py-1 text-xs text-zinc-400 transition-colors hover:bg-zinc-800 hover:text-white"
                                >
                                    Fit
                                </button>
                                <span className="inline-flex items-center gap-1 rounded-lg border border-zinc-800 px-2 py-1 text-xs text-zinc-500">
                                    <Hand size={12} />
                                    Drag
                                </span>
                                <button
                                    onClick={handleResetZoom}
                                    className="p-2 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-white transition-colors"
                                >
                                    <RotateCcw size={18} />
                                </button>
                                <div className="w-px h-6 bg-zinc-800 mx-2" />
                                <button
                                    onClick={handleCloseFullscreen}
                                    className="p-2 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-white transition-colors"
                                >
                                    <X size={18} />
                                </button>
                            </div>
                        </div>

                        {/* Fullscreen Diagram */}
                        <div
                            ref={fullscreenCanvasRef}
                            className={`flex-1 overflow-auto p-6 md:p-8 ${zoom > 1 ? 'cursor-grab' : 'cursor-default'} ${isPanning ? 'cursor-grabbing select-none' : ''}`}
                            onPointerDown={handleCanvasPointerDown}
                            onPointerMove={handleCanvasPointerMove}
                            onPointerUp={stopPanning}
                            onPointerLeave={stopPanning}
                            onPointerCancel={stopPanning}
                        >
                            <div
                                className="flex min-h-full min-w-full items-center justify-center"
                            >
                                <div
                                    className="relative"
                                    style={{
                                        width: scaledWidth,
                                        height: scaledHeight,
                                    }}
                                >
                                    <div
                                        style={{
                                            width: baseWidth,
                                            height: baseHeight,
                                            transform: `scale(${zoom})`,
                                            transformOrigin: 'top left',
                                        }}
                                        className="transition-transform duration-150"
                                    >
                                        <div
                                            style={{
                                                width: svgDimensions.width,
                                                height: svgDimensions.height,
                                                transform: `translate(${-contentBounds.x}px, ${-contentBounds.y}px)`,
                                                transformOrigin: 'top left',
                                            }}
                                            dangerouslySetInnerHTML={{ __html: svg }}
                                        />
                                    </div>
                                </div>
                            </div>
                            <div
                                className="pointer-events-none fixed bottom-4 left-1/2 z-10 -translate-x-1/2 rounded-full border border-zinc-700 bg-zinc-900/80 px-3 py-1 text-xs text-zinc-300"
                                style={{
                                    display: zoom >= 1 ? 'block' : 'none',
                                }}
                            >
                                Hand drag enabled • Fit to re-center
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </>
    );
}
