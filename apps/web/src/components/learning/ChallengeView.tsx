'use client';

import { ReactNode, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Bug, Eye, Edit3, Check, X, Lightbulb, ChevronRight, Zap, Loader2 } from 'lucide-react';
import {
    api,
    BugHuntChallengeData,
    Challenge,
    ChallengeResult,
    CodeTraceChallengeData,
    FillBlankChallengeData,
    FillBlankValidationItem,
} from '@/lib/api-client';

interface ChallengeViewProps {
    repoId: string;
    challenge: Challenge;
    onComplete: (result: ChallengeResult, usedHint: boolean) => void;
    onClose: () => void;
}

// Challenge Type Icons
const CHALLENGE_ICONS: Record<Challenge['challenge_type'], ReactNode> = {
    bug_hunt: <Bug size={20} />,
    code_trace: <Eye size={20} />,
    fill_blank: <Edit3 size={20} />,
};

const CHALLENGE_LABELS: Record<Challenge['challenge_type'], string> = {
    bug_hunt: 'Bug Hunt',
    code_trace: 'Code Trace',
    fill_blank: 'Fill in the Blank',
};

const CHALLENGE_COLORS: Record<Challenge['challenge_type'], string> = {
    bug_hunt: 'from-red-600 to-orange-600',
    code_trace: 'from-blue-600 to-cyan-600',
    fill_blank: 'from-purple-600 to-pink-600',
};

export function ChallengeView({ repoId, challenge, onComplete, onClose }: ChallengeViewProps) {
    const [showHint, setShowHint] = useState(false);
    const [result, setResult] = useState<ChallengeResult | null>(null);
    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const xpAwarded = result?.xp_gained
        ? result.xp_gained.amount + (result.xp_gained.bonus ?? 0)
        : (result?.xp_earned ?? 0);

    const handleValidate = async (answer: number | string[]) => {
        if (submitting || result) {
            return;
        }

        setSubmitting(true);
        setError(null);

        try {
            const validation = await api.validateChallenge(
                repoId,
                challenge.challenge_type,
                challenge,
                answer,
                showHint
            );
            setResult(validation);
            onComplete(validation, showHint);
        } catch (validationError) {
            console.error('Failed to validate challenge:', validationError);
            setError('Could not validate your answer. Please try again.');
        } finally {
            setSubmitting(false);
        }
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
                                <p className="text-sm text-white/80">Scored by backend validation</p>
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
                            data={challenge.data as BugHuntChallengeData}
                            onSubmit={handleValidate}
                            showHint={showHint}
                            result={result}
                            submitting={submitting}
                        />
                    )}
                    {challenge.challenge_type === 'code_trace' && (
                        <CodeTraceChallenge
                            data={challenge.data as CodeTraceChallengeData}
                            onSubmit={handleValidate}
                            showHint={showHint}
                            result={result}
                            submitting={submitting}
                        />
                    )}
                    {challenge.challenge_type === 'fill_blank' && (
                        <FillBlankChallenge
                            data={challenge.data as FillBlankChallengeData}
                            onSubmit={handleValidate}
                            showHint={showHint}
                            result={result}
                            submitting={submitting}
                        />
                    )}
                </div>

                {/* Footer */}
                <div className="border-t border-zinc-800 p-4 flex items-center justify-between gap-3">
                    <button
                        onClick={() => setShowHint(true)}
                        disabled={showHint || submitting || Boolean(result)}
                        className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${showHint
                                ? 'bg-yellow-500/10 text-yellow-400/50 cursor-not-allowed'
                                : 'bg-yellow-500/10 text-yellow-400 hover:bg-yellow-500/20'
                            }`}
                    >
                        <Lightbulb size={16} />
                        {showHint ? 'Hint Used' : 'Show Hint'}
                    </button>

                    <div className="flex items-center gap-3">
                        {error && (
                            <span className="text-sm text-red-400">{error}</span>
                        )}

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
                                            <span className="font-medium">Correct! +{xpAwarded} XP</span>
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
                </div>
            </motion.div>
        </motion.div>
    );
}


// =============================================================================
// Bug Hunt Challenge
// =============================================================================

interface BugHuntChallengeProps {
    data: BugHuntChallengeData;
    onSubmit: (selectedLine: number) => void;
    showHint: boolean;
    result: ChallengeResult | null;
    submitting: boolean;
}

function BugHuntChallenge({ data, onSubmit, showHint, result, submitting }: BugHuntChallengeProps) {
    const [selectedLine, setSelectedLine] = useState<number | null>(null);

    const lines = data.code_snippet.split('\n');
    const submitted = Boolean(result);
    const correctLine = result?.correct_line ?? data.bug_line;

    const handleSubmit = () => {
        if (selectedLine === null) return;
        onSubmit(selectedLine);
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
                            const isCorrect = submitted && lineNum === correctLine;
                            const isWrong = submitted && isSelected && lineNum !== correctLine;

                            return (
                                <div
                                    key={idx}
                                    onClick={() => !submitted && !submitting && setSelectedLine(lineNum)}
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
                    <strong>Explanation:</strong> {result?.explanation || data.bug_description}
                </motion.div>
            )}

            {!submitted && (
                <button
                    onClick={handleSubmit}
                    disabled={selectedLine === null || submitting}
                    className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium rounded-xl flex items-center justify-center gap-2 transition-all"
                >
                    {submitting ? <Loader2 size={18} className="animate-spin" /> : 'Submit Answer'}
                    {!submitting && <ChevronRight size={18} />}
                </button>
            )}
        </div>
    );
}


// =============================================================================
// Code Trace Challenge
// =============================================================================

interface CodeTraceChallengeProps {
    data: CodeTraceChallengeData;
    onSubmit: (selectedIndex: number) => void;
    showHint: boolean;
    result: ChallengeResult | null;
    submitting: boolean;
}

function CodeTraceChallenge({ data, onSubmit, showHint, result, submitting }: CodeTraceChallengeProps) {
    const [selectedOption, setSelectedOption] = useState<number | null>(null);

    const submitted = Boolean(result);
    const correctIndex = result?.correct_index ?? data.correct_index;

    const handleSubmit = () => {
        if (selectedOption === null) return;
        onSubmit(selectedOption);
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
                    const isCorrect = submitted && idx === correctIndex;
                    const isWrong = submitted && isSelected && idx !== correctIndex;

                    return (
                        <button
                            key={idx}
                            onClick={() => !submitted && !submitting && setSelectedOption(idx)}
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
                    <strong>Explanation:</strong> {result?.explanation || data.explanation}
                </motion.div>
            )}

            {!submitted && (
                <button
                    onClick={handleSubmit}
                    disabled={selectedOption === null || submitting}
                    className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium rounded-xl flex items-center justify-center gap-2 transition-all"
                >
                    {submitting ? <Loader2 size={18} className="animate-spin" /> : 'Submit Answer'}
                    {!submitting && <ChevronRight size={18} />}
                </button>
            )}
        </div>
    );
}


// =============================================================================
// Fill in the Blank Challenge
// =============================================================================

interface FillBlankChallengeProps {
    data: FillBlankChallengeData;
    onSubmit: (answers: string[]) => void;
    showHint: boolean;
    result: ChallengeResult | null;
    submitting: boolean;
}

function FillBlankChallenge({ data, onSubmit, showHint, result, submitting }: FillBlankChallengeProps) {
    const [answers, setAnswers] = useState<Record<string, string>>({});

    const submitted = Boolean(result);
    const validationMap = useMemo<Record<string, FillBlankValidationItem>>(() => {
        const items = result?.results ?? [];
        return items.reduce<Record<string, FillBlankValidationItem>>((acc, item) => {
            acc[item.id] = item;
            return acc;
        }, {});
    }, [result]);

    const handleSubmit = () => {
        const orderedAnswers = data.blanks.map((blank) => answers[blank.id] || '');
        onSubmit(orderedAnswers);
    };

    const renderCodeWithBlanks = () => {
        const codeDisplay = data.code_with_blanks;

        return (
            <pre className="text-sm font-mono text-zinc-300 whitespace-pre-wrap">
                {codeDisplay.split('___').map((part, idx) => {
                    const blank = data.blanks[idx];
                    const validation = blank ? validationMap[blank.id] : undefined;

                    return (
                        <span key={idx}>
                            {part}
                            {blank && (
                                <select
                                    value={answers[blank.id] || ''}
                                    onChange={(event) => setAnswers({ ...answers, [blank.id]: event.target.value })}
                                    disabled={submitted || submitting}
                                    className={`mx-1 px-2 py-1 rounded border transition-all ${submitted
                                            ? validation?.correct
                                                ? 'bg-green-500/20 border-green-500 text-green-300'
                                                : 'bg-red-500/20 border-red-500 text-red-300'
                                            : 'bg-zinc-800 border-zinc-600 text-white'
                                        }`}
                                >
                                    <option value="">Select...</option>
                                    {blank.options.map((option) => (
                                        <option key={option} value={option}>{option}</option>
                                    ))}
                                </select>
                            )}
                        </span>
                    );
                })}
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
                    <strong>Correct answers:</strong> {data.blanks.map((blank) => blank.answer).join(', ')}
                </motion.div>
            )}

            {!submitted && (
                <button
                    onClick={handleSubmit}
                    disabled={Object.keys(answers).length < data.blanks.length || submitting}
                    className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed text-white font-medium rounded-xl flex items-center justify-center gap-2 transition-all"
                >
                    {submitting ? <Loader2 size={18} className="animate-spin" /> : 'Submit Answer'}
                    {!submitting && <ChevronRight size={18} />}
                </button>
            )}
        </div>
    );
}


// =============================================================================
// Challenge Button (for lesson view integration)
// =============================================================================

interface ChallengeButtonProps {
    type: Challenge['challenge_type'];
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
