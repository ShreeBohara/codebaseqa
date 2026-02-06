import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import { Challenge, ChallengeResult, CodeReference, LessonContent, Quiz, QuizResultResponse, UserStats, api } from '@/lib/api-client';
import { FileCode, Layers, X, Maximize2, Minimize2, Loader2, Award, Check, Bug, Eye, Edit3, Download } from 'lucide-react';
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
    content: LessonContent;
    onClose: () => void;
    onComplete?: (xpGain: XPGainResult) => void;
    onGamificationUpdate?: (xpGain: XPGainResult, stats?: UserStats) => void;
}

export function LessonView({ repoId, content, onClose, onComplete, onGamificationUpdate }: LessonViewProps) {
    const [activeRef, setActiveRef] = useState<CodeReference | null>(
        content.code_references.length > 0 ? content.code_references[0] : null
    );
    const [isFullscreen, setIsFullscreen] = useState(false);
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

    useEffect(() => {
        async function loadContent() {
            if (!activeRef) {
                setFileContent(null);
                return;
            }
            setLoadingFile(true);
            try {
                const data = await api.getRepoFileContent(repoId, activeRef.file_path);
                setFileContent(data.content);
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
            const tour = await api.exportCodeTour(repoId, content.id);
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
            const result = await api.completeLesson(repoId, content.id, 300); // Mock time spent

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
            <div className="h-14 border-b border-zinc-800 flex items-center justify-between px-6 bg-zinc-900/50 backdrop-blur relative z-10">
                <div className="flex items-center gap-4">
                    <button
                        onClick={onClose}
                        className="p-2 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-white transition-colors"
                    >
                        <X size={20} />
                    </button>
                    <div>
                        <h2 className="font-semibold text-white">{content.title}</h2>
                        <div className="flex items-center gap-2 text-xs text-zinc-500">
                            <span className="flex items-center gap-1">
                                <Layers size={12} />
                                {content.code_references.length} code references
                            </span>
                        </div>
                    </div>

                    <button
                        onClick={handleExportCodeTour}
                        disabled={downloading}
                        className="p-2 ml-2 hover:bg-zinc-800 rounded-lg text-zinc-400 hover:text-indigo-400 transition-colors"
                        title="Export as VS Code Tour"
                    >
                        {downloading ? <Loader2 size={20} className="animate-spin" /> : <Download size={20} />}
                    </button>
                </div>

                <div className="flex items-center gap-2">
                    {/* Challenge Buttons */}
                    <div className="flex items-center gap-1 mr-2">
                        <button
                            onClick={() => handleStartChallenge('bug_hunt')}
                            disabled={generatingChallenge}
                            className="bg-red-600/10 hover:bg-red-600/20 text-red-400 px-3 py-1.5 rounded-lg text-sm font-medium flex items-center gap-1.5 transition-colors disabled:opacity-50"
                            title="Bug Hunt Challenge"
                        >
                            <Bug size={14} />
                            <span className="hidden sm:inline">Bug Hunt</span>
                        </button>
                        <button
                            onClick={() => handleStartChallenge('code_trace')}
                            disabled={generatingChallenge}
                            className="bg-blue-600/10 hover:bg-blue-600/20 text-blue-400 px-3 py-1.5 rounded-lg text-sm font-medium flex items-center gap-1.5 transition-colors disabled:opacity-50"
                            title="Code Trace Challenge"
                        >
                            <Eye size={14} />
                            <span className="hidden sm:inline">Trace</span>
                        </button>
                        <button
                            onClick={() => handleStartChallenge('fill_blank')}
                            disabled={generatingChallenge}
                            className="bg-purple-600/10 hover:bg-purple-600/20 text-purple-400 px-3 py-1.5 rounded-lg text-sm font-medium flex items-center gap-1.5 transition-colors disabled:opacity-50"
                            title="Fill in the Blank Challenge"
                        >
                            <Edit3 size={14} />
                            <span className="hidden sm:inline">Fill</span>
                        </button>
                    </div>

                    {/* Quiz Button */}
                    <button
                        onClick={handleTakeQuiz}
                        disabled={generatingQuiz}
                        className="bg-indigo-600/10 hover:bg-indigo-600/20 text-indigo-400 px-4 py-1.5 rounded-lg text-sm font-medium flex items-center gap-2 transition-colors"
                    >
                        {generatingQuiz ? <Loader2 className="animate-spin" size={16} /> : <Award size={16} />}
                        {generatingQuiz ? 'Generating Quiz...' : 'Take Quiz'}
                    </button>
                </div>
            </div>

            <div className="flex-1 flex overflow-hidden">
                {/* Left Panel: Content */}
                {!isFullscreen && (
                    <div className="w-1/2 overflow-y-auto border-r border-zinc-800 p-10">
                        <div className="max-w-3xl mx-auto">
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
                <div className={`${isFullscreen ? 'w-full' : 'w-1/2'} flex flex-col bg-zinc-950`}>
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
