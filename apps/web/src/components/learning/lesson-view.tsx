import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import { Challenge, ChallengeResult, CodeReference, LessonContent, Quiz, QuizResultResponse, UserStats, api } from '@/lib/api-client';
import { FileCode, Layers, X, Maximize2, Minimize2, Loader2, Award, Check, Bug, Eye, Edit3, Download, RotateCw, BookOpen, ChevronDown } from 'lucide-react';
import { RepoContextBadge } from '@/components/common/repo-context-badge';
import { QuizView } from './quiz-view';
import { MermaidDiagram } from './MermaidDiagram';
import { ChallengeView } from './ChallengeView';
import confetti from 'canvas-confetti';

interface XPGainResult {
    amount: number;
    reason: string;
    bonus?: number;
}

interface LessonViewProps {
    repoId: string;
    repoName?: string;
    content: LessonContent;
    persona?: string;
    moduleId?: string;
    onRegenerate?: () => Promise<void> | void;
    onClose: () => void;
    onComplete?: (xpGain: XPGainResult) => void;
    onGamificationUpdate?: (xpGain: XPGainResult, stats?: UserStats) => void;
}

const PERSONA_MISSIONS: Record<string, string> = {
    new_hire: 'Focus on fast onboarding and first safe delivery.',
    auditor: 'Focus on trust boundaries, validation paths, and security risk.',
    fullstack: 'Focus on end-to-end flow from UI through backend and storage.',
    archaeologist: 'Focus on legacy decisions, evolution, and debt hotspots.',
};

export function LessonView({
    repoId,
    repoName,
    content,
    persona,
    moduleId,
    onRegenerate,
    onClose,
    onComplete,
    onGamificationUpdate,
}: LessonViewProps) {
    const [activeRef, setActiveRef] = useState<CodeReference | null>(
        content.code_references.length > 0 ? content.code_references[0] : null
    );
    const [isFullscreen, setIsFullscreen] = useState(false);
    const [mobilePanel, setMobilePanel] = useState<'content' | 'code'>('content');
    const [fileContent, setFileContent] = useState<string | null>(null);
    const [loadingFile, setLoadingFile] = useState(false);

    // Quiz State
    const [showQuiz, setShowQuiz] = useState(false);
    const [quiz, setQuiz] = useState<Quiz | null>(null);
    const [generatingQuiz, setGeneratingQuiz] = useState(false);

    // Challenge State
    const [showChallenge, setShowChallenge] = useState(false);
    const [challenge, setChallenge] = useState<Challenge | null>(null);
    const [generatingChallenge, setGeneratingChallenge] = useState(false);
    const [downloading, setDownloading] = useState(false);
    const [regenerating, setRegenerating] = useState(false);

    useEffect(() => {
        setActiveRef(content.code_references.length > 0 ? content.code_references[0] : null);
    }, [content]);

    useEffect(() => {
        async function loadContent() {
            if (!activeRef) {
                setFileContent(null);
                return;
            }
            setLoadingFile(true);
            try {
                const data = await api.getRepoFileContent(repoId, activeRef.file_path);
                setFileContent(data?.content ?? null);
            } catch (e) {
                console.error('Failed to load file content:', e);
                setFileContent(null);
            } finally {
                setLoadingFile(false);
            }
        }

        loadContent();
    }, [repoId, activeRef]);

    const handleTakeQuiz = async () => {
        if (quiz) {
            setShowQuiz(true);
            return;
        }

        setGeneratingQuiz(true);
        try {
            const data = await api.generateQuiz(repoId, content.id, content.content_markdown);
            setQuiz(data);
            setShowQuiz(true);
        } catch (error) {
            console.error("Failed to generate quiz:", error);
            alert("Could not generate quiz. Please try again.");
        } finally {
            setGeneratingQuiz(false);
        }
    };

    const handleStartChallenge = async (type: 'bug_hunt' | 'code_trace' | 'fill_blank') => {
        setGeneratingChallenge(true);
        try {
            const data = await api.generateChallenge(repoId, content.id, type, content.content_markdown);
            setChallenge(data);
            setShowChallenge(true);
        } catch (error) {
            console.error("Failed to generate challenge:", error);
            alert("Could not generate challenge. Please try again.");
        } finally {
            setGeneratingChallenge(false);
        }
    };

    const handleChallengeComplete = (result: ChallengeResult, usedHint: boolean) => {
        if (result.correct && result.xp_gained) {
            onGamificationUpdate?.(result.xp_gained, result.stats);
        }
        console.log(`Challenge completed: correct=${result.correct}, usedHint=${usedHint}`);
    };

    const handleQuizResultSubmitted = (result: QuizResultResponse) => {
        if (result.xp_gained.amount > 0 || (result.xp_gained.bonus ?? 0) > 0) {
            onGamificationUpdate?.(result.xp_gained, result.stats);
        }
    };

    const handleExportCodeTour = async () => {
        setDownloading(true);
        try {
            const tour = await api.exportCodeTour(repoId, content.id, { persona });
            // Create blob and download
            const blob = new Blob([JSON.stringify(tour, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${content.title.replace(/\\s+/g, '_').toLowerCase()}.tour`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        } catch (error) {
            console.error("Failed to export CodeTour:", error);
            alert("Could not export CodeTour. Please try again.");
        } finally {
            setDownloading(false);
        }
    };

    const handleFinishLesson = async () => {
        try {
            const result = await api.completeLesson(repoId, content.id, 300, {
                persona,
                moduleId,
            }); // Mock time spent

            // Trigger Confetti
            confetti({
                particleCount: 100,
                spread: 70,
                origin: { y: 0.6 }
            });

            onComplete?.(result.xp_gained);
            if (onClose) onClose();

        } catch (error) {
            console.error("Failed to complete lesson:", error);
        }
    };

    const handleRegenerate = async () => {
        if (!onRegenerate || regenerating) return;
        setRegenerating(true);
        try {
            await onRegenerate();
        } finally {
            setRegenerating(false);
        }
    };

    const qualityMeta = (content.quality_meta ?? {}) as Record<string, unknown>;
    const hasQualityMeta = Object.keys(qualityMeta).length > 0;
    const quizLabel = generatingQuiz ? 'Generating Quiz...' : quiz ? 'Retake Quiz' : 'Take Quiz';

    const closeActionMenus = () => {
        if (typeof document === 'undefined') return;
        document.querySelectorAll('details[data-action-menu]').forEach((node) => {
            (node as HTMLDetailsElement).open = false;
        });
    };

    return (
        <div className="fixed inset-0 z-50 bg-zinc-950 flex flex-col pt-16 animate-in fade-in duration-300">

            {/* Quiz Overlay */}
            <AnimatePresence>
                {showQuiz && quiz && (
                    <motion.div
                        initial={{ opacity: 0, y: 50 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: 50 }}
                        className="absolute inset-x-0 bottom-0 top-16 z-50 bg-zinc-950"
                    >
                        <div className="absolute top-4 right-4 z-10 w-full flex justify-end px-4">
                            <button onClick={() => setShowQuiz(false)} className="p-2 hover:bg-zinc-800 rounded-lg text-zinc-400">
                                <X size={24} />
                            </button>
                        </div>
                        <QuizView
                            repoId={repoId}
                            quiz={quiz}
                            onClose={() => setShowQuiz(false)}
                            onResultSubmitted={handleQuizResultSubmitted}
                        />
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Challenge Overlay */}
            <AnimatePresence>
                {showChallenge && challenge && (
                    <ChallengeView
                        repoId={repoId}
                        challenge={challenge}
                        onComplete={handleChallengeComplete}
                        onClose={() => setShowChallenge(false)}
                    />
                )}
            </AnimatePresence>

            {/* Toolbar */}
            <div className="relative z-10 border-b border-zinc-800/90 bg-zinc-950/90 px-3 py-2.5 backdrop-blur-md sm:px-4">
                <div className="relative flex min-h-9 items-center justify-between gap-2">
                    <button
                        onClick={onClose}
                        className="relative z-10 inline-flex h-9 w-9 items-center justify-center rounded-md text-zinc-400 transition-colors hover:bg-zinc-800/80 hover:text-white"
                        title="Close lesson"
                    >
                        <X size={18} />
                    </button>

                    <h2
                        title={content.title}
                        className="pointer-events-none absolute inset-x-16 mx-auto truncate px-1 text-center text-[15px] font-medium tracking-tight text-zinc-100 sm:text-base"
                    >
                        {content.title}
                    </h2>

                    <div className="relative z-10 flex items-center gap-1.5">
                        <button
                            onClick={handleTakeQuiz}
                            disabled={generatingQuiz}
                            className="inline-flex h-9 items-center gap-1.5 rounded-md border border-indigo-500/35 bg-indigo-500/10 px-2.5 text-sm font-medium text-indigo-100 transition-colors hover:bg-indigo-500/20 disabled:opacity-50 sm:px-3"
                        >
                            {generatingQuiz ? <Loader2 className="animate-spin" size={16} /> : <Award size={16} />}
                            <span className="hidden md:inline">{quizLabel}</span>
                        </button>

                        <details data-action-menu className="relative">
                            <summary className="inline-flex h-9 list-none cursor-pointer items-center gap-1 rounded-md border border-zinc-700/90 bg-zinc-900/90 px-2.5 text-sm text-zinc-200 transition-colors hover:bg-zinc-800/90 [&::-webkit-details-marker]:hidden sm:px-3">
                                <span className="hidden sm:inline">Actions</span>
                                <ChevronDown size={14} className="text-zinc-400" />
                            </summary>
                            <div className="absolute right-0 mt-2 w-60 rounded-lg border border-zinc-700/90 bg-zinc-950/95 p-1.5 shadow-2xl">
                                <p className="px-2 py-1 text-[11px] uppercase tracking-wider text-zinc-500">Practice</p>
                                <button
                                    onClick={() => {
                                        closeActionMenus();
                                        handleStartChallenge('bug_hunt');
                                    }}
                                    disabled={generatingChallenge}
                                    className="w-full rounded-lg px-3 py-2 text-left text-sm text-zinc-200 hover:bg-zinc-800 disabled:opacity-50"
                                >
                                    <span className="inline-flex items-center gap-2"><Bug size={14} className="text-red-400" />Bug Hunt</span>
                                </button>
                                <button
                                    onClick={() => {
                                        closeActionMenus();
                                        handleStartChallenge('code_trace');
                                    }}
                                    disabled={generatingChallenge}
                                    className="w-full rounded-lg px-3 py-2 text-left text-sm text-zinc-200 hover:bg-zinc-800 disabled:opacity-50"
                                >
                                    <span className="inline-flex items-center gap-2"><Eye size={14} className="text-blue-400" />Trace Flow</span>
                                </button>
                                <button
                                    onClick={() => {
                                        closeActionMenus();
                                        handleStartChallenge('fill_blank');
                                    }}
                                    disabled={generatingChallenge}
                                    className="w-full rounded-lg px-3 py-2 text-left text-sm text-zinc-200 hover:bg-zinc-800 disabled:opacity-50"
                                >
                                    <span className="inline-flex items-center gap-2"><Edit3 size={14} className="text-violet-300" />Fill Blanks</span>
                                </button>
                                <div className="my-1 h-px bg-zinc-800" />
                                <p className="px-2 py-1 text-[11px] uppercase tracking-wider text-zinc-500">Lesson Tools</p>
                                <button
                                    onClick={() => {
                                        closeActionMenus();
                                        handleRegenerate();
                                    }}
                                    disabled={!onRegenerate || regenerating}
                                    className="w-full rounded-lg px-3 py-2 text-left text-sm text-zinc-200 hover:bg-zinc-800 disabled:opacity-50"
                                >
                                    <span className="inline-flex items-center gap-2">
                                        {regenerating ? <Loader2 size={14} className="animate-spin text-amber-300" /> : <RotateCw size={14} className="text-amber-300" />}
                                        Regenerate lesson
                                    </span>
                                </button>
                                <button
                                    onClick={() => {
                                        closeActionMenus();
                                        handleExportCodeTour();
                                    }}
                                    disabled={downloading}
                                    className="w-full rounded-lg px-3 py-2 text-left text-sm text-zinc-200 hover:bg-zinc-800 disabled:opacity-50"
                                >
                                    <span className="inline-flex items-center gap-2">
                                        {downloading ? <Loader2 size={14} className="animate-spin text-indigo-300" /> : <Download size={14} className="text-indigo-300" />}
                                        Export CodeTour
                                    </span>
                                </button>
                            </div>
                        </details>
                    </div>
                </div>

                <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-[11px] text-zinc-500 sm:pl-10">
                    {repoName && (
                        <RepoContextBadge
                            repoName={repoName}
                            compact
                            className="max-w-[260px] border-zinc-800 bg-zinc-900/60"
                        />
                    )}
                    <div tabIndex={0} className="group relative outline-none">
                        <span className="inline-flex cursor-default items-center gap-1 rounded-md border border-zinc-800/90 bg-zinc-900/60 px-2 py-0.5">
                            <Layers size={12} />
                            {content.code_references.length} refs
                        </span>
                        {content.code_references.length > 0 && (
                            <div className="pointer-events-none invisible absolute left-0 top-[calc(100%+8px)] z-30 w-[360px] max-w-[88vw] rounded-xl border border-zinc-800 bg-zinc-950/95 p-2 opacity-0 shadow-2xl transition-all duration-150 group-hover:visible group-hover:opacity-100 group-focus-within:visible group-focus-within:opacity-100">
                                <p className="px-1 pb-1 text-[10px] uppercase tracking-wider text-zinc-500">Code References</p>
                                <div className="space-y-1">
                                    {content.code_references.map((ref, index) => (
                                        <div key={`${ref.file_path}:${ref.start_line}:${ref.end_line}:${index}`} className="flex items-center justify-between gap-3 rounded-lg bg-zinc-900/70 px-2 py-1.5 text-xs">
                                            <span className="truncate text-zinc-200">{ref.file_path}</span>
                                            <span className="shrink-0 text-zinc-500">L{ref.start_line}-{ref.end_line}</span>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                    {persona && (
                        <span className="inline-flex items-center gap-1 rounded-md border border-zinc-800/90 bg-zinc-900/60 px-2 py-0.5 text-zinc-300">
                            <BookOpen size={10} />
                            {persona.replace('_', ' ')}
                        </span>
                    )}
                </div>

                {content.cache_info && (
                    <div className="mt-2 text-xs text-zinc-500">
                        <span className="mr-3">Source: {content.cache_info.source}</span>
                        {content.cache_info.generated_at && <span className="mr-3">Generated: {new Date(content.cache_info.generated_at).toLocaleString()}</span>}
                        {content.cache_info.expires_at && <span>Expires: {new Date(content.cache_info.expires_at).toLocaleString()}</span>}
                    </div>
                )}

                {!isFullscreen && (
                    <div className="mt-3 grid grid-cols-2 gap-2 lg:hidden">
                        <button
                            onClick={() => setMobilePanel('content')}
                            className={`rounded-lg px-3 py-2 text-sm ${mobilePanel === 'content' ? 'bg-zinc-800 text-white' : 'bg-zinc-900 text-zinc-400'}`}
                        >
                            Lesson
                        </button>
                        <button
                            onClick={() => setMobilePanel('code')}
                            className={`rounded-lg px-3 py-2 text-sm ${mobilePanel === 'code' ? 'bg-zinc-800 text-white' : 'bg-zinc-900 text-zinc-400'}`}
                        >
                            Code Evidence
                        </button>
                    </div>
                )}
            </div>

            <div className="flex-1 flex flex-col lg:flex-row overflow-hidden">
                {/* Left Panel: Content */}
                {!isFullscreen && (
                    <div className={`${mobilePanel === 'content' ? 'block' : 'hidden'} lg:block w-full lg:w-1/2 overflow-y-auto border-r border-zinc-800 p-6 lg:p-10`}>
                        <div className="max-w-3xl mx-auto">
                            {persona && (
                                <div className="mb-5 rounded-lg border border-zinc-800/80 bg-zinc-900/40 px-3 py-2">
                                    <p className="text-[10px] uppercase tracking-wider text-zinc-500">Mission Lens</p>
                                    <p className="mt-0.5 text-sm text-zinc-300">
                                        {PERSONA_MISSIONS[persona] || 'Focus on role-specific mastery for this lesson.'}
                                    </p>
                                </div>
                            )}
                            {/* Mermaid Diagram - Now Rendered */}
                            {content.diagram_mermaid && (
                                <MermaidDiagram
                                    code={content.diagram_mermaid}
                                    className="mb-10"
                                />
                            )}

                            {/* Lesson Content with improved typography */}
                            <div className="prose prose-invert prose-zinc prose-lg max-w-none">
                                <ReactMarkdown
                                    components={{
                                        h1: ({ children }) => (
                                            <h1 className="text-2xl font-bold text-white mb-6 pb-3 border-b border-zinc-800">
                                                {children}
                                            </h1>
                                        ),
                                        h2: ({ children }) => (
                                            <h2 className="text-xl font-semibold text-white mt-10 mb-4 flex items-center gap-3">
                                                <span className="w-1 h-6 bg-indigo-500 rounded-full" />
                                                {children}
                                            </h2>
                                        ),
                                        h3: ({ children }) => (
                                            <h3 className="text-lg font-medium text-zinc-200 mt-6 mb-3">
                                                {children}
                                            </h3>
                                        ),
                                        p: ({ children }) => (
                                            <p className="text-base text-zinc-300 leading-relaxed mb-4">
                                                {children}
                                            </p>
                                        ),
                                        ul: ({ children }) => (
                                            <ul className="space-y-2 mb-6 ml-1">
                                                {children}
                                            </ul>
                                        ),
                                        li: ({ children }) => (
                                            <li className="text-base text-zinc-300 leading-relaxed flex gap-3">
                                                <span className="text-indigo-400 mt-1.5">•</span>
                                                <span>{children}</span>
                                            </li>
                                        ),
                                        strong: ({ children }) => (
                                            <strong className="font-semibold text-white">
                                                {children}
                                            </strong>
                                        ),
                                        code: ({ children }) => (
                                            <code className="bg-zinc-800/80 px-2 py-1 rounded-md text-indigo-300 font-mono text-sm border border-zinc-700/50">
                                                {children}
                                            </code>
                                        ),
                                        pre: ({ children }) => (
                                            <pre className="bg-zinc-900 border border-zinc-800 rounded-xl p-4 overflow-x-auto mb-6">
                                                {children}
                                            </pre>
                                        ),
                                    }}
                                >
                                    {content.content_markdown}
                                </ReactMarkdown>
                            </div>
                        </div>

                        {/* Finish Button */}
                        <div className="mt-12 flex justify-center">
                            <button
                                onClick={handleFinishLesson}
                                className="px-8 py-3 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-xl shadow-lg shadow-indigo-500/20 flex items-center gap-2 transform transition-all hover:scale-105"
                            >
                                <Check size={20} />
                                Finish Lesson
                            </button>
                        </div>
                    </div>
                )}

                {/* Right Panel: Code Viewer */}
                <div className={`${isFullscreen ? 'w-full flex' : mobilePanel === 'code' ? 'w-full flex' : 'hidden lg:flex lg:w-1/2'} flex-col bg-zinc-950`}>
                    {/* File Tabs */}
                    {content.code_references.length > 0 ? (
                        <>
                            <div className="flex overflow-x-auto border-b border-zinc-800 bg-zinc-900/30">
                                {content.code_references.map((ref, idx) => (
                                    <button
                                        key={idx}
                                        onClick={() => setActiveRef(ref)}
                                        className={`
                      px-4 py-3 text-sm font-mono flex items-center gap-2 border-r border-zinc-800 min-w-max transition-colors
                      ${activeRef === ref
                                                ? 'bg-zinc-950 text-indigo-400 border-t-2 border-t-indigo-500'
                                                : 'text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900'
                                            }
                    `}
                                    >
                                        <FileCode size={14} />
                                        {ref.file_path.split('/').pop()}
                                    </button>
                                ))}

                                <div className="flex-1" />

                                <button
                                    onClick={() => setIsFullscreen(!isFullscreen)}
                                    className="px-4 text-zinc-500 hover:text-white"
                                    title={isFullscreen ? "Exit Fullscreen" : "Fullscreen Code"}
                                >
                                    {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
                                </button>
                            </div>

                            {/* Code Display */}
                            <div className="flex-1 overflow-auto p-4 bg-[#0d0d12]">
                                {hasQualityMeta && (
                                    <div className="mb-3 rounded-lg border border-zinc-800 bg-zinc-900/60 p-2 text-xs text-zinc-400">
                                        Evidence Score: sections {String(qualityMeta.section_score ?? 'n/a')} | persona {String(qualityMeta.persona_term_score ?? 'n/a')} | refs {String(qualityMeta.reference_count ?? content.code_references.length)}
                                    </div>
                                )}
                                {activeRef ? (
                                    <div className="font-mono text-sm relative">
                                        <div className="mb-4 text-xs text-zinc-500 p-2 bg-zinc-900/50 rounded border border-zinc-800 flex justify-between">
                                            <span>File: {activeRef.file_path}</span>
                                            <span>Lines {activeRef.start_line}-{activeRef.end_line}</span>
                                        </div>

                                        <div className="p-4 rounded bg-zinc-900/30 border border-zinc-800 text-zinc-400 mb-6">
                                            <p className="mb-2 text-indigo-400 font-semibold text-xs uppercase tracking-wider">Instructor Note:</p>
                                            <p>{activeRef.description}</p>
                                        </div>

                                        {loadingFile ? (
                                            <div className="flex items-center justify-center py-20 text-zinc-600">
                                                <Loader2 className="animate-spin" />
                                            </div>
                                        ) : fileContent ? (
                                            <div className="relative overflow-x-auto">
                                                <pre className="text-zinc-300">
                                                    <code>
                                                        {fileContent.split('\n').map((line, i) => {
                                                            const lineNum = i + 1;
                                                            const isHighlighted = lineNum >= activeRef.start_line && lineNum <= activeRef.end_line;

                                                            return (
                                                                <div
                                                                    key={i}
                                                                    className={`${isHighlighted ? 'bg-indigo-500/10 border-l-2 border-indigo-500' : 'opacity-50 hover:opacity-100'} px-4 py-0.5 transition-opacity`}
                                                                    ref={isHighlighted && lineNum === activeRef.start_line ? (el) => el?.scrollIntoView({ block: 'center', behavior: 'smooth' }) : undefined}
                                                                >
                                                                    <span className="inline-block w-8 text-right mr-4 text-zinc-600 select-none text-xs">{lineNum}</span>
                                                                    <span>{line}</span>
                                                                </div>
                                                            );
                                                        })}
                                                    </code>
                                                </pre>
                                            </div>
                                        ) : (
                                            <div className="flex flex-col items-center justify-center py-16 text-center">
                                                <FileCode size={40} className="text-zinc-700 mb-4" />
                                                <p className="text-zinc-400 mb-2">Could not load file content</p>
                                                <p className="text-zinc-600 text-sm mb-6">The file may have been moved or renamed.</p>
                                                <div className="flex gap-3">
                                                    <button
                                                        onClick={() => {
                                                            setFileContent(null);
                                                            setLoadingFile(true);
                                                            api.getRepoFileContent(repoId, activeRef.file_path)
                                                                .then(data => setFileContent(data.content))
                                                                .catch(() => setFileContent(null))
                                                                .finally(() => setLoadingFile(false));
                                                        }}
                                                        className="px-4 py-2 text-sm bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded-lg transition-colors"
                                                    >
                                                        Retry
                                                    </button>
                                                    {content.code_references.length > 1 && (
                                                        <button
                                                            onClick={() => {
                                                                const currentIndex = content.code_references.findIndex(r => r === activeRef);
                                                                const nextIndex = (currentIndex + 1) % content.code_references.length;
                                                                setActiveRef(content.code_references[nextIndex]);
                                                            }}
                                                            className="px-4 py-2 text-sm bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-400 rounded-lg transition-colors"
                                                        >
                                                            Skip to Next
                                                        </button>
                                                    )}
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                ) : (
                                    <div className="flex flex-col items-center justify-center h-full text-zinc-500">
                                        <FileCode size={48} className="mb-4 opacity-20" />
                                        <p>Select a file to view code</p>
                                    </div>
                                )}
                            </div>
                        </>
                    ) : (
                        <div className="flex flex-col items-center justify-center h-full text-zinc-500">
                            <Layers size={48} className="mb-4 opacity-20" />
                            <p>No code references in this lesson</p>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
