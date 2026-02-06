import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Check, X, ArrowRight, Award, Loader2 } from 'lucide-react';
import { api, Quiz, QuizResultResponse } from '@/lib/api-client';
import confetti from 'canvas-confetti';

interface QuizViewProps {
    repoId: string;
    quiz: Quiz;
    onClose: () => void;
    onResultSubmitted?: (result: QuizResultResponse) => void;
}

export function QuizView({ repoId, quiz, onClose, onResultSubmitted }: QuizViewProps) {
    const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
    const [selectedOption, setSelectedOption] = useState<number | null>(null);
    const [isAnswered, setIsAnswered] = useState(false);
    const [score, setScore] = useState(0);
    const [showResult, setShowResult] = useState(false);
    const [submittingResult, setSubmittingResult] = useState(false);
    const [resultError, setResultError] = useState<string | null>(null);
    const [backendResult, setBackendResult] = useState<QuizResultResponse | null>(null);

    const currentQuestion = quiz.questions[currentQuestionIndex];
    const isCorrect = selectedOption === currentQuestion.correct_option_index;

    const handleSelectOption = (index: number) => {
        if (isAnswered || submittingResult) return;
        setSelectedOption(index);
        setIsAnswered(true);

        if (index === currentQuestion.correct_option_index) {
            setScore((value) => value + 1);
            confetti({
                particleCount: 50,
                spread: 60,
                origin: { y: 0.8 },
                colors: ['#6366f1', '#818cf8'],
            });
        }
    };

    const submitQuizResult = async () => {
        const totalQuestions = quiz.questions.length;
        const normalizedScore = totalQuestions > 0 ? score / totalQuestions : 0;

        setSubmittingResult(true);
        setResultError(null);

        try {
            const result = await api.submitQuizResult(repoId, quiz.lesson_id, normalizedScore);
            setBackendResult(result);
            onResultSubmitted?.(result);
            setShowResult(true);
            confetti({
                particleCount: 150,
                spread: 100,
                origin: { y: 0.6 },
            });
        } catch (error) {
            console.error('Failed to submit quiz result:', error);
            setResultError('Could not submit quiz result. Try again.');
        } finally {
            setSubmittingResult(false);
        }
    };

    const handleNext = async () => {
        if (currentQuestionIndex < quiz.questions.length - 1) {
            setCurrentQuestionIndex((value) => value + 1);
            setSelectedOption(null);
            setIsAnswered(false);
            return;
        }

        await submitQuizResult();
    };

    if (showResult) {
        const xpAwarded = backendResult
            ? backendResult.xp_gained.amount + (backendResult.xp_gained.bonus ?? 0)
            : 0;

        return (
            <div className="flex flex-col items-center justify-center h-full p-8 text-center animate-in fade-in zoom-in duration-300">
                <div className="w-20 h-20 bg-yellow-500/20 rounded-full flex items-center justify-center mb-6">
                    <Award size={40} className="text-yellow-500" />
                </div>
                <h2 className="text-3xl font-bold text-white mb-2">Quiz Complete!</h2>
                <p className="text-zinc-400 mb-4">
                    You scored <span className="text-white font-bold">{score}</span> out of{' '}
                    <span className="text-white font-bold">{quiz.questions.length}</span>
                </p>

                {backendResult && (
                    <p className="text-sm text-indigo-300 mb-8">
                        {backendResult.is_perfect
                            ? `Perfect score! +${xpAwarded} XP`
                            : backendResult.is_pass
                                ? `Passed! +${xpAwarded} XP`
                                : 'Keep practicing to pass the quiz.'}
                    </p>
                )}

                <div className="flex gap-4">
                    <button
                        onClick={onClose}
                        className="bg-zinc-800 hover:bg-zinc-700 text-white px-6 py-2 rounded-lg transition-colors"
                    >
                        Close Quiz
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="flex flex-col h-full bg-zinc-950 p-6 max-w-2xl mx-auto">
            {/* Header */}
            <div className="flex justify-between items-center mb-8">
                <div className="text-zinc-500 text-sm font-medium">
                    Question {currentQuestionIndex + 1} of {quiz.questions.length}
                </div>
                <div className="text-indigo-400 font-bold">
                    Score: {score}
                </div>
            </div>

            {/* Progress Bar */}
            <div className="w-full bg-zinc-900 h-1 rounded-full mb-8 overflow-hidden">
                <div
                    className="bg-indigo-600 h-full transition-all duration-300"
                    style={{ width: `${((currentQuestionIndex + 1) / quiz.questions.length) * 100}%` }}
                />
            </div>

            {/* Question */}
            <div className="flex-1">
                <h3 className="text-xl text-white font-semibold mb-6">
                    {currentQuestion.text}
                </h3>

                <div className="space-y-3">
                    {currentQuestion.options.map((option, idx) => {
                        let className = 'w-full p-4 rounded-xl border-2 text-left transition-all relative ';

                        if (isAnswered) {
                            if (idx === currentQuestion.correct_option_index) {
                                className += 'border-green-500 bg-green-500/10 text-green-100';
                            } else if (idx === selectedOption) {
                                className += 'border-red-500 bg-red-500/10 text-red-100 opacity-60';
                            } else {
                                className += 'border-zinc-800 bg-zinc-900/50 text-zinc-500 opacity-50';
                            }
                        } else {
                            className += 'border-zinc-800 bg-zinc-900 hover:bg-zinc-800 hover:border-zinc-700 text-zinc-300';
                        }

                        return (
                            <button
                                key={idx}
                                onClick={() => handleSelectOption(idx)}
                                disabled={isAnswered || submittingResult}
                                className={className}
                            >
                                <div className="flex items-center justify-between">
                                    <span>{option}</span>
                                    {isAnswered && idx === currentQuestion.correct_option_index && (
                                        <Check size={20} className="text-green-500" />
                                    )}
                                    {isAnswered && idx === selectedOption && idx !== currentQuestion.correct_option_index && (
                                        <X size={20} className="text-red-500" />
                                    )}
                                </div>
                            </button>
                        );
                    })}
                </div>

                {/* Feedback / Next Button */}
                <AnimatePresence>
                    {isAnswered && (
                        <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            className="mt-8"
                        >
                            <div className={`p-4 rounded-lg mb-6 ${isCorrect ? 'bg-green-500/10 border border-green-500/20' : 'bg-red-500/10 border border-red-500/20'}`}>
                                <p className={`font-semibold mb-1 ${isCorrect ? 'text-green-400' : 'text-red-400'}`}>
                                    {isCorrect ? 'Correct!' : 'Incorrect'}
                                </p>
                                <p className="text-zinc-300 text-sm">
                                    {currentQuestion.explanation}
                                </p>
                            </div>

                            {resultError && (
                                <p className="text-sm text-red-400 mb-4">{resultError}</p>
                            )}

                            <button
                                onClick={handleNext}
                                disabled={submittingResult}
                                className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 text-white font-medium py-3 rounded-xl flex items-center justify-center gap-2 transition-colors"
                            >
                                {submittingResult ? (
                                    <>
                                        <Loader2 size={18} className="animate-spin" />
                                        Submitting...
                                    </>
                                ) : (
                                    <>
                                        {currentQuestionIndex < quiz.questions.length - 1 ? 'Next Question' : 'Finish Quiz'}
                                        <ArrowRight size={18} />
                                    </>
                                )}
                            </button>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </div>
    );
}
