'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bug, Eye, Edit3, Check, X, Lightbulb, ChevronRight, Zap } from 'lucide-react';

interface Challenge {
    id: string;
    lesson_id: string;
    challenge_type: string;
    data: any;
    completed: boolean;
    used_hint: boolean;
}

interface ChallengeViewProps {
    challenge: Challenge;
    onComplete: (correct: boolean, usedHint: boolean) => void;
    onClose: () => void;
}

// Challenge Type Icons
const CHALLENGE_ICONS: Record<string, React.ReactNode> = {
    bug_hunt: <Bug size={20} />,
    code_trace: <Eye size={20} />,
    fill_blank: <Edit3 size={20} />
};

const CHALLENGE_LABELS: Record<string, string> = {
    bug_hunt: 'Bug Hunt',
    code_trace: 'Code Trace',
    fill_blank: 'Fill in the Blank'
};

const CHALLENGE_COLORS: Record<string, string> = {
    bug_hunt: 'from-red-600 to-orange-600',
    code_trace: 'from-blue-600 to-cyan-600',
    fill_blank: 'from-purple-600 to-pink-600'
};

export function ChallengeView({ challenge, onComplete, onClose }: ChallengeViewProps) {
    const [showHint, setShowHint] = useState(false);
    const [result, setResult] = useState<{ correct: boolean; explanation?: string } | null>(null);

    const handleComplete = (correct: boolean, explanation?: string) => {
        setResult({ correct, explanation });
        // Delay to show result before closing
        setTimeout(() => {
            onComplete(correct, showHint);
        }, 2000);
    };

    return (
        <motion.div
            className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
        >
            <motion.div
                className="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col"
                initial={{ scale: 0.95, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.95, opacity: 0 }}
            >
                {/* Header */}
                <div className={`bg-gradient-to-r ${CHALLENGE_COLORS[challenge.challenge_type]} p-4`}>
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3 text-white">
                            <div className="w-10 h-10 rounded-xl bg-white/20 flex items-center justify-center">
                                {CHALLENGE_ICONS[challenge.challenge_type]}
                            </div>
                            <div>
                                <h2 className="font-bold text-lg">{CHALLENGE_LABELS[challenge.challenge_type]}</h2>
                                <p className="text-sm text-white/80">+75 XP on completion</p>
                            </div>
                        </div>
                        <button
                            onClick={onClose}
                            className="p-2 hover:bg-white/20 rounded-lg transition-colors"
                        >
                            <X size={20} className="text-white" />
                        </button>
                    </div>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-6">
                    {challenge.challenge_type === 'bug_hunt' && (
                        <BugHuntChallenge
                            data={challenge.data}
                            onComplete={handleComplete}
                            showHint={showHint}
                        />
                    )}
                    {challenge.challenge_type === 'code_trace' && (
                        <CodeTraceChallenge
                            data={challenge.data}
                            onComplete={handleComplete}
                            showHint={showHint}
                        />
                    )}
                    {challenge.challenge_type === 'fill_blank' && (
                        <FillBlankChallenge
                            data={challenge.data}
                            onComplete={handleComplete}
                            showHint={showHint}
                        />
                    )}
                </div>

                {/* Footer */}
                <div className="border-t border-zinc-800 p-4 flex items-center justify-between">
                    <button
                        onClick={() => setShowHint(true)}
                        disabled={showHint}
                        className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${showHint
                                ? 'bg-yellow-500/10 text-yellow-400/50 cursor-not-allowed'
                                : 'bg-yellow-500/10 text-yellow-400 hover:bg-yellow-500/20'
                            }`}
                    >
                        <Lightbulb size={16} />
                        {showHint ? 'Hint Used' : 'Show Hint'}
                    </button>

                    {/* Result Display */}
                    <AnimatePresence>
                        {result && (
                            <motion.div
                                initial={{ opacity: 0, x: 20 }}
                                animate={{ opacity: 1, x: 0 }}
                                className={`flex items-center gap-2 px-4 py-2 rounded-lg ${result.correct
                                        ? 'bg-green-500/20 text-green-400'
                                        : 'bg-red-500/20 text-red-400'
                                    }`}
                            >
                                {result.correct ? (
                                    <>
                                        <Check size={18} />
                                        <span className="font-medium">Correct! +75 XP</span>
                                    </>
                                ) : (
                                    <>
                                        <X size={18} />
                                        <span className="font-medium">Incorrect</span>
                                    </>
                                )}
                            </motion.div>
                        )}
                    </AnimatePresence>
                </div>
            </motion.div>
        </motion.div>
    );
}


// =============================================================================
// Bug Hunt Challenge
// =============================================================================

interface BugHuntChallengeProps {
    data: {
        description: string;
        code_snippet: string;
        bug_line: number;
        bug_description: string;
        hint: string;
    };
    onComplete: (correct: boolean, explanation: string) => void;
    showHint: boolean;
}

function BugHuntChallenge({ data, onComplete, showHint }: BugHuntChallengeProps) {
    const [selectedLine, setSelectedLine] = useState<number | null>(null);
    const [submitted, setSubmitted] = useState(false);

    const lines = data.code_snippet.split('\n');

    const handleSubmit = () => {
        if (selectedLine === null) return;
        setSubmitted(true);
        const correct = selectedLine === data.bug_line;
        onComplete(correct, data.bug_description);
    };

    return (
        <div className="space-y-4">
            <p className="text-zinc-300">{data.description}</p>

            {showHint && (
                <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3 text-yellow-300 text-sm"
                >
                    💡 <strong>Hint:</strong> {data.hint}
                </motion.div>
            )}

            <div className="bg-zinc-950 rounded-xl overflow-hidden border border-zinc-800">
                <div className="p-3 border-b border-zinc-800 text-xs text-zinc-500">
                    Click on the line with the bug
                </div>
                <div className="p-4 overflow-x-auto">
                    <pre className="text-sm font-mono">
                        {lines.map((line, idx) => {
                            const lineNum = idx + 1;
                            const isSelected = selectedLine === lineNum;
                            const isCorrect = submitted && lineNum === data.bug_line;
                            const isWrong = submitted && isSelected && lineNum !== data.bug_line;

                            return (
                                <div
                                    key={idx}
                                    onClick={() => !submitted && setSelectedLine(lineNum)}
                                    className={`flex cursor-pointer transition-all rounded px-2 py-0.5 ${isCorrect
                                            ? 'bg-green-500/20 border-l-2 border-green-500'
                                            : isWrong
                                                ? 'bg-red-500/20 border-l-2 border-red-500'
                                                : isSelected
                                                    ? 'bg-indigo-500/20 border-l-2 border-indigo-500'
                                                    : 'hover:bg-zinc-800/50'
                                        }`}
                                >
                                    <span className="w-8 text-zinc-600 select-none">{lineNum}</span>
                                    <code className={`${isCorrect ? 'text-green-300' : isWrong ? 'text-red-300' : 'text-zinc-300'}`}>
                                        {line || ' '}
                                    </code>
                                </div>
                            );
                        })}
                    </pre>
                </div>
            </div>

            {submitted && (
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-zinc-800/50 rounded-lg p-4 text-sm text-zinc-300"
                >
                    <strong>Explanation:</strong> {data.bug_description}
                </motion.div>
            )}

            {!submitted && (
                <button
                    onClick={handleSubmit}
                    disabled={selectedLine === null}
                    className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium rounded-xl flex items-center justify-center gap-2 transition-all"
                >
                    Submit Answer
                    <ChevronRight size={18} />
                </button>
            )}
        </div>
    );
}


// =============================================================================
// Code Trace Challenge
// =============================================================================

interface CodeTraceChallengeProps {
    data: {
        description: string;
        code_snippet: string;
        question: string;
        options: string[];
        correct_index: number;
        explanation: string;
    };
    onComplete: (correct: boolean, explanation: string) => void;
    showHint: boolean;
}

function CodeTraceChallenge({ data, onComplete, showHint }: CodeTraceChallengeProps) {
    const [selectedOption, setSelectedOption] = useState<number | null>(null);
    const [submitted, setSubmitted] = useState(false);

    const handleSubmit = () => {
        if (selectedOption === null) return;
        setSubmitted(true);
        const correct = selectedOption === data.correct_index;
        onComplete(correct, data.explanation);
    };

    return (
        <div className="space-y-4">
            <p className="text-zinc-300">{data.description}</p>

            {showHint && (
                <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3 text-yellow-300 text-sm"
                >
                    💡 <strong>Hint:</strong> Trace through the code step by step
                </motion.div>
            )}

            <div className="bg-zinc-950 rounded-xl overflow-hidden border border-zinc-800">
                <div className="p-4 overflow-x-auto">
                    <pre className="text-sm font-mono text-zinc-300">{data.code_snippet}</pre>
                </div>
            </div>

            <p className="text-white font-medium">{data.question}</p>

            <div className="grid grid-cols-2 gap-3">
                {data.options.map((option, idx) => {
                    const isSelected = selectedOption === idx;
                    const isCorrect = submitted && idx === data.correct_index;
                    const isWrong = submitted && isSelected && idx !== data.correct_index;

                    return (
                        <button
                            key={idx}
                            onClick={() => !submitted && setSelectedOption(idx)}
                            className={`p-4 rounded-xl border text-left font-mono transition-all ${isCorrect
                                    ? 'bg-green-500/20 border-green-500 text-green-300'
                                    : isWrong
                                        ? 'bg-red-500/20 border-red-500 text-red-300'
                                        : isSelected
                                            ? 'bg-indigo-500/20 border-indigo-500 text-indigo-300'
                                            : 'bg-zinc-800/50 border-zinc-700 text-zinc-300 hover:border-zinc-600'
                                }`}
                        >
                            {option}
                        </button>
                    );
                })}
            </div>

            {submitted && (
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-zinc-800/50 rounded-lg p-4 text-sm text-zinc-300"
                >
                    <strong>Explanation:</strong> {data.explanation}
                </motion.div>
            )}

            {!submitted && (
                <button
                    onClick={handleSubmit}
                    disabled={selectedOption === null}
                    className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium rounded-xl flex items-center justify-center gap-2 transition-all"
                >
                    Submit Answer
                    <ChevronRight size={18} />
                </button>
            )}
        </div>
    );
}


// =============================================================================
// Fill in the Blank Challenge
// =============================================================================

interface FillBlankChallengeProps {
    data: {
        description: string;
        code_with_blanks: string;
        blanks: Array<{ id: string; answer: string; options: string[] }>;
    };
    onComplete: (correct: boolean, explanation: string) => void;
    showHint: boolean;
}

function FillBlankChallenge({ data, onComplete, showHint }: FillBlankChallengeProps) {
    const [answers, setAnswers] = useState<Record<string, string>>({});
    const [submitted, setSubmitted] = useState(false);
    const [results, setResults] = useState<Record<string, boolean>>({});

    const handleSubmit = () => {
        setSubmitted(true);

        const newResults: Record<string, boolean> = {};
        let allCorrect = true;

        data.blanks.forEach((blank) => {
            const correct = answers[blank.id]?.toLowerCase() === blank.answer.toLowerCase();
            newResults[blank.id] = correct;
            if (!correct) allCorrect = false;
        });

        setResults(newResults);
        onComplete(allCorrect, `Answers: ${data.blanks.map(b => b.answer).join(', ')}`);
    };

    // Render code with interactive blanks
    const renderCodeWithBlanks = () => {
        let codeDisplay = data.code_with_blanks;

        return (
            <pre className="text-sm font-mono text-zinc-300 whitespace-pre-wrap">
                {codeDisplay.split('___').map((part, idx) => (
                    <span key={idx}>
                        {part}
                        {idx < data.blanks.length && (
                            <select
                                value={answers[data.blanks[idx].id] || ''}
                                onChange={(e) => setAnswers({ ...answers, [data.blanks[idx].id]: e.target.value })}
                                disabled={submitted}
                                className={`mx-1 px-2 py-1 rounded border transition-all ${submitted
                                        ? results[data.blanks[idx].id]
                                            ? 'bg-green-500/20 border-green-500 text-green-300'
                                            : 'bg-red-500/20 border-red-500 text-red-300'
                                        : 'bg-zinc-800 border-zinc-600 text-white'
                                    }`}
                            >
                                <option value="">Select...</option>
                                {data.blanks[idx].options.map((opt) => (
                                    <option key={opt} value={opt}>{opt}</option>
                                ))}
                            </select>
                        )}
                    </span>
                ))}
            </pre>
        );
    };

    return (
        <div className="space-y-4">
            <p className="text-zinc-300">{data.description}</p>

            {showHint && (
                <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-3 text-yellow-300 text-sm"
                >
                    💡 <strong>Hint:</strong> Think about the common patterns used for this type of code
                </motion.div>
            )}

            <div className="bg-zinc-950 rounded-xl overflow-hidden border border-zinc-800">
                <div className="p-3 border-b border-zinc-800 text-xs text-zinc-500">
                    Fill in the missing parts
                </div>
                <div className="p-4 overflow-x-auto">
                    {renderCodeWithBlanks()}
                </div>
            </div>

            {submitted && (
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="bg-zinc-800/50 rounded-lg p-4 text-sm text-zinc-300"
                >
                    <strong>Correct answers:</strong> {data.blanks.map(b => b.answer).join(', ')}
                </motion.div>
            )}

            {!submitted && (
                <button
                    onClick={handleSubmit}
                    disabled={Object.keys(answers).length < data.blanks.length}
                    className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium rounded-xl flex items-center justify-center gap-2 transition-all"
                >
                    Submit Answer
                    <ChevronRight size={18} />
                </button>
            )}
        </div>
    );
}


// =============================================================================
// Challenge Button (for lesson view integration)
// =============================================================================

interface ChallengeButtonProps {
    type: 'bug_hunt' | 'code_trace' | 'fill_blank';
    onClick: () => void;
    disabled?: boolean;
}

export function ChallengeButton({ type, onClick, disabled }: ChallengeButtonProps) {
    return (
        <button
            onClick={onClick}
            disabled={disabled}
            className={`flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r ${CHALLENGE_COLORS[type]} text-white font-medium text-sm shadow-lg transition-all hover:shadow-xl hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed`}
        >
            {CHALLENGE_ICONS[type]}
            {CHALLENGE_LABELS[type]}
            <Zap size={14} className="text-yellow-300" />
        </button>
    );
}
