'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { Flame, TrendingUp, Zap } from 'lucide-react';

interface XPBarProps {
    totalXP: number;
    level: number;
    levelTitle: string;
    levelIcon: string;
    xpProgress: number;  // 0.0 - 1.0
    xpForNextLevel: number;
    streak: number;
    compact?: boolean;
}

export function XPBar({
    totalXP,
    level,
    levelTitle,
    levelIcon,
    xpProgress,
    xpForNextLevel,
    streak,
    compact = false
}: XPBarProps) {
    if (compact) {
        return (
            <div className="flex items-center gap-3">
                {/* Level Badge */}
                <div className="flex items-center gap-1.5 px-2 py-1 bg-gradient-to-r from-indigo-600/20 to-purple-600/20 border border-indigo-500/30 rounded-lg">
                    <span className="text-sm">{levelIcon}</span>
                    <span className="text-xs font-bold text-indigo-300">Lv.{level}</span>
                </div>

                {/* XP Progress Mini */}
                <div className="flex items-center gap-2">
                    <div className="w-20 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                        <motion.div
                            className="h-full bg-gradient-to-r from-indigo-500 to-purple-500"
                            initial={{ width: 0 }}
                            animate={{ width: `${xpProgress * 100}%` }}
                            transition={{ duration: 0.5, ease: 'easeOut' }}
                        />
                    </div>
                    <span className="text-xs text-zinc-500 font-mono">{totalXP} XP</span>
                </div>

                {/* Streak */}
                {streak > 0 && (
                    <div className="flex items-center gap-1 text-orange-400">
                        <Flame size={14} className="animate-pulse" />
                        <span className="text-xs font-bold">{streak}</span>
                    </div>
                )}
            </div>
        );
    }

    return (
        <div className="bg-zinc-900/80 border border-zinc-800 rounded-xl p-4">
            {/* Header */}
            <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-3">
                    {/* Level Badge */}
                    <div className="relative">
                        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-600/30 to-purple-600/30 border border-indigo-500/40 flex items-center justify-center text-2xl">
                            {levelIcon}
                        </div>
                        <div className="absolute -bottom-1 -right-1 px-1.5 py-0.5 bg-indigo-600 rounded text-[10px] font-bold text-white">
                            {level}
                        </div>
                    </div>

                    <div>
                        <h3 className="font-semibold text-white">{levelTitle}</h3>
                        <p className="text-xs text-zinc-500">Level {level}</p>
                    </div>
                </div>

                {/* Streak Badge */}
                {streak > 0 && (
                    <motion.div
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        className="flex items-center gap-1.5 px-3 py-1.5 bg-orange-500/10 border border-orange-500/30 rounded-lg"
                    >
                        <Flame size={16} className="text-orange-400 animate-pulse" />
                        <span className="text-sm font-bold text-orange-300">{streak} day streak</span>
                    </motion.div>
                )}
            </div>

            {/* XP Progress Bar */}
            <div className="space-y-1.5">
                <div className="flex justify-between items-center text-xs">
                    <span className="text-zinc-400 flex items-center gap-1">
                        <Zap size={12} className="text-yellow-400" />
                        {totalXP} XP
                    </span>
                    <span className="text-zinc-500">
                        {xpForNextLevel} XP to level {level + 1}
                    </span>
                </div>

                <div className="h-2.5 bg-zinc-800 rounded-full overflow-hidden">
                    <motion.div
                        className="h-full bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 rounded-full"
                        initial={{ width: 0 }}
                        animate={{ width: `${xpProgress * 100}%` }}
                        transition={{ duration: 0.8, ease: 'easeOut' }}
                    />
                </div>
            </div>
        </div>
    );
}


// Floating XP gain animation
interface XPGainPopupProps {
    amount: number;
    bonus?: number;
    onComplete?: () => void;
}

export function XPGainPopup({ amount, bonus, onComplete }: XPGainPopupProps) {
    return (
        <motion.div
            className="fixed top-20 right-8 z-50"
            initial={{ opacity: 0, y: 20, scale: 0.8 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
            onAnimationComplete={() => {
                setTimeout(() => onComplete?.(), 2000);
            }}
        >
            <div className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white px-4 py-2 rounded-xl shadow-lg shadow-indigo-500/30 flex items-center gap-2">
                <Zap size={18} className="text-yellow-300" />
                <span className="font-bold text-lg">+{amount} XP</span>
                {bonus && bonus > 0 && (
                    <span className="text-xs bg-white/20 px-1.5 py-0.5 rounded">
                        +{bonus} streak bonus
                    </span>
                )}
            </div>
        </motion.div>
    );
}
