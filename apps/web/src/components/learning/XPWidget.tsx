'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Trophy, Flame, Zap, ChevronUp } from 'lucide-react';
import { UserStats } from '@/lib/api-client';

interface XPWidgetProps {
    stats: UserStats | null;
    onOpenAchievements: () => void;
}

const LEVEL_COLORS: Record<number, string> = {
    1: 'from-emerald-500 to-teal-500',
    2: 'from-blue-500 to-cyan-500',
    3: 'from-violet-500 to-purple-500',
    4: 'from-orange-500 to-amber-500',
    5: 'from-rose-500 to-pink-500',
    6: 'from-yellow-400 to-amber-400',
};

export function XPWidget({ stats, onOpenAchievements }: XPWidgetProps) {
    const [isExpanded, setIsExpanded] = useState(false);

    if (!stats) return null;

    const levelColor = LEVEL_COLORS[stats.level.level] || LEVEL_COLORS[1];

    return (
        <motion.div
            className="fixed bottom-6 right-6 z-40"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
        >
            {/* Expanded Panel */}
            <AnimatePresence>
                {isExpanded && (
                    <motion.div
                        initial={{ opacity: 0, y: 10, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 10, scale: 0.95 }}
                        className="absolute bottom-full right-0 mb-3 w-72"
                    >
                        <div className="bg-slate-900/95 backdrop-blur-xl border border-slate-700/50 rounded-2xl p-5 shadow-2xl">
                            {/* Header */}
                            <div className="flex items-center gap-3 mb-4">
                                <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${levelColor} flex items-center justify-center text-white font-bold text-lg shadow-lg`}>
                                    {stats.level.icon}
                                </div>
                                <div>
                                    <h3 className="font-semibold text-white">{stats.level.title}</h3>
                                    <p className="text-sm text-slate-400">Level {stats.level.level}</p>
                                </div>
                            </div>

                            {/* XP Progress */}
                            <div className="mb-4">
                                <div className="flex justify-between text-sm mb-1.5">
                                    <span className="text-slate-400">Progress</span>
                                    <span className="text-white font-medium">{stats.total_xp} / {stats.level.xp_for_next_level} XP</span>
                                </div>
                                <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                                    <motion.div
                                        initial={{ width: 0 }}
                                        animate={{ width: `${stats.level.xp_progress * 100}%` }}
                                        className={`h-full bg-gradient-to-r ${levelColor}`}
                                    />
                                </div>
                            </div>

                            {/* Stats Grid */}
                            <div className="grid grid-cols-2 gap-3 mb-4">
                                <div className="bg-slate-800/50 rounded-xl p-3 text-center">
                                    <div className="text-2xl font-bold text-white">{stats.lessons_completed}</div>
                                    <div className="text-xs text-slate-400">Lessons</div>
                                </div>
                                <div className="bg-slate-800/50 rounded-xl p-3 text-center">
                                    <div className="text-2xl font-bold text-white">{stats.quizzes_passed}</div>
                                    <div className="text-xs text-slate-400">Quizzes</div>
                                </div>
                                <div className="bg-slate-800/50 rounded-xl p-3 text-center">
                                    <div className="text-2xl font-bold text-white">{stats.challenges_completed}</div>
                                    <div className="text-xs text-slate-400">Challenges</div>
                                </div>
                                <div className="bg-slate-800/50 rounded-xl p-3 text-center">
                                    <div className="text-2xl font-bold text-orange-400">{stats.streak.current}</div>
                                    <div className="text-xs text-slate-400">Day Streak</div>
                                </div>
                            </div>

                            {/* Achievements Button */}
                            <button
                                onClick={onOpenAchievements}
                                className="w-full py-2.5 bg-gradient-to-r from-amber-500 to-orange-500 text-white font-medium rounded-xl flex items-center justify-center gap-2 hover:shadow-lg hover:shadow-orange-500/20 transition-all"
                            >
                                <Trophy size={16} />
                                View Achievements
                            </button>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Main Widget Button */}
            <motion.button
                onClick={() => setIsExpanded(!isExpanded)}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className={`relative bg-slate-900/95 backdrop-blur-xl border border-slate-700/50 rounded-2xl p-4 shadow-2xl flex items-center gap-3 hover:border-slate-600 transition-colors`}
            >
                {/* Level Badge */}
                <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${levelColor} flex items-center justify-center text-white font-bold shadow-lg`}>
                    {stats.level.level}
                </div>

                {/* Info */}
                <div className="text-left">
                    <div className="text-sm font-medium text-white flex items-center gap-1.5">
                        {stats.total_xp} XP
                        {stats.streak.current > 0 && (
                            <span className="flex items-center text-orange-400">
                                <Flame size={14} className="ml-1" />
                                {stats.streak.current}
                            </span>
                        )}
                    </div>
                    <div className="text-xs text-slate-400">{stats.level.title}</div>
                </div>

                {/* Expand Indicator */}
                <motion.div
                    animate={{ rotate: isExpanded ? 180 : 0 }}
                    className="text-slate-500"
                >
                    <ChevronUp size={16} />
                </motion.div>

                {/* Glow effect */}
                <div className={`absolute inset-0 rounded-2xl bg-gradient-to-r ${levelColor} opacity-0 hover:opacity-10 transition-opacity pointer-events-none`} />
            </motion.button>
        </motion.div>
    );
}

// Floating XP Gain Animation
export function XPGainFloat({ amount, x, y }: { amount: number; x: number; y: number }) {
    return (
        <motion.div
            initial={{ opacity: 1, y: 0, scale: 1 }}
            animate={{ opacity: 0, y: -60, scale: 1.2 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 1.5 }}
            className="fixed z-50 pointer-events-none"
            style={{ left: x, top: y }}
        >
            <div className="flex items-center gap-1 text-emerald-400 font-bold text-lg">
                <Zap size={18} />
                +{amount} XP
            </div>
        </motion.div>
    );
}
