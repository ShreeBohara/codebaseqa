'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { Award, Lock, Check } from 'lucide-react';

interface Achievement {
    key: string;
    name: string;
    description: string;
    icon: string;
    category: string;
    xp_reward: number;
    requirement?: number;
    unlocked: boolean;
}

interface AchievementsPanelProps {
    achievements: Achievement[];
    onClose?: () => void;
}

const CATEGORY_LABELS: Record<string, { label: string; color: string }> = {
    learning: { label: 'Learning', color: 'from-blue-500 to-indigo-500' },
    streak: { label: 'Streaks', color: 'from-orange-500 to-red-500' },
    explorer: { label: 'Explorer', color: 'from-green-500 to-emerald-500' },
    challenge: { label: 'Challenges', color: 'from-purple-500 to-pink-500' },
};

export function AchievementsPanel({ achievements, onClose }: AchievementsPanelProps) {
    const grouped = achievements.reduce((acc, a) => {
        if (!acc[a.category]) acc[a.category] = [];
        acc[a.category].push(a);
        return acc;
    }, {} as Record<string, Achievement[]>);

    const unlocked = achievements.filter(a => a.unlocked).length;
    const total = achievements.length;

    return (
        <div className="bg-zinc-900/95 border border-zinc-800 rounded-2xl overflow-hidden max-w-2xl w-full max-h-[80vh] flex flex-col">
            {/* Header */}
            <div className="p-6 border-b border-zinc-800 bg-gradient-to-r from-zinc-900 to-zinc-800">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-yellow-500/20 flex items-center justify-center">
                            <Award size={24} className="text-yellow-400" />
                        </div>
                        <div>
                            <h2 className="text-xl font-bold text-white">Achievements</h2>
                            <p className="text-sm text-zinc-400">
                                {unlocked} of {total} unlocked
                            </p>
                        </div>
                    </div>

                    {/* Progress Ring */}
                    <div className="relative w-16 h-16">
                        <svg className="w-full h-full transform -rotate-90">
                            <circle
                                cx="32"
                                cy="32"
                                r="28"
                                stroke="currentColor"
                                strokeWidth="4"
                                fill="none"
                                className="text-zinc-800"
                            />
                            <motion.circle
                                cx="32"
                                cy="32"
                                r="28"
                                stroke="url(#gradient)"
                                strokeWidth="4"
                                fill="none"
                                strokeLinecap="round"
                                initial={{ strokeDasharray: '0 176' }}
                                animate={{ strokeDasharray: `${(unlocked / total) * 176} 176` }}
                                transition={{ duration: 1, ease: 'easeOut' }}
                            />
                            <defs>
                                <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                                    <stop offset="0%" stopColor="#6366f1" />
                                    <stop offset="100%" stopColor="#a855f7" />
                                </linearGradient>
                            </defs>
                        </svg>
                        <div className="absolute inset-0 flex items-center justify-center">
                            <span className="text-lg font-bold text-white">
                                {Math.round((unlocked / total) * 100)}%
                            </span>
                        </div>
                    </div>
                </div>
            </div>

            {/* Categories */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
                {Object.entries(grouped).map(([category, categoryAchievements]) => {
                    const info = CATEGORY_LABELS[category] || { label: category, color: 'from-gray-500 to-gray-600' };
                    const categoryUnlocked = categoryAchievements.filter(a => a.unlocked).length;

                    return (
                        <div key={category}>
                            {/* Category Header */}
                            <div className="flex items-center justify-between mb-3">
                                <h3 className={`text-sm font-semibold bg-gradient-to-r ${info.color} bg-clip-text text-transparent`}>
                                    {info.label}
                                </h3>
                                <span className="text-xs text-zinc-500">
                                    {categoryUnlocked}/{categoryAchievements.length}
                                </span>
                            </div>

                            {/* Achievement Grid */}
                            <div className="grid grid-cols-2 gap-3">
                                {categoryAchievements.map((achievement, idx) => (
                                    <motion.div
                                        key={achievement.key}
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        transition={{ delay: idx * 0.05 }}
                                        className={`
                                            relative p-3 rounded-xl border transition-all
                                            ${achievement.unlocked
                                                ? 'bg-zinc-800/50 border-zinc-700 hover:border-zinc-600'
                                                : 'bg-zinc-900/50 border-zinc-800/50 opacity-60'
                                            }
                                        `}
                                    >
                                        <div className="flex items-start gap-3">
                                            {/* Icon */}
                                            <div className={`
                                                text-2xl w-10 h-10 rounded-lg flex items-center justify-center
                                                ${achievement.unlocked
                                                    ? 'bg-gradient-to-br from-yellow-500/20 to-orange-500/20'
                                                    : 'bg-zinc-800 grayscale'
                                                }
                                            `}>
                                                {achievement.unlocked ? (
                                                    achievement.icon
                                                ) : (
                                                    <Lock size={16} className="text-zinc-600" />
                                                )}
                                            </div>

                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-1.5">
                                                    <h4 className={`text-sm font-medium truncate ${achievement.unlocked ? 'text-white' : 'text-zinc-500'}`}>
                                                        {achievement.name}
                                                    </h4>
                                                    {achievement.unlocked && (
                                                        <Check size={12} className="text-green-400 flex-shrink-0" />
                                                    )}
                                                </div>
                                                <p className="text-xs text-zinc-500 line-clamp-2">
                                                    {achievement.description}
                                                </p>
                                            </div>
                                        </div>

                                        {/* XP Badge */}
                                        <div className={`
                                            absolute top-2 right-2 px-1.5 py-0.5 rounded text-[10px] font-mono
                                            ${achievement.unlocked
                                                ? 'bg-indigo-500/20 text-indigo-300'
                                                : 'bg-zinc-800 text-zinc-600'
                                            }
                                        `}>
                                            +{achievement.xp_reward} XP
                                        </div>
                                    </motion.div>
                                ))}
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}


// Achievement unlock toast
interface AchievementToastProps {
    achievement: {
        name: string;
        icon: string;
        xp_reward: number;
    };
    onComplete?: () => void;
}

export function AchievementToast({ achievement, onComplete }: AchievementToastProps) {
    return (
        <motion.div
            className="fixed top-24 right-8 z-50"
            initial={{ opacity: 0, x: 100, scale: 0.8 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 100 }}
            transition={{ type: 'spring', damping: 15 }}
            onAnimationComplete={() => {
                setTimeout(() => onComplete?.(), 3000);
            }}
        >
            <div className="bg-gradient-to-r from-yellow-600/90 to-orange-600/90 backdrop-blur-sm text-white px-5 py-3 rounded-xl shadow-lg shadow-orange-500/30 flex items-center gap-3">
                <div className="text-2xl animate-bounce">{achievement.icon}</div>
                <div>
                    <p className="text-xs text-yellow-200 uppercase tracking-wider">Achievement Unlocked!</p>
                    <p className="font-bold">{achievement.name}</p>
                </div>
                <div className="ml-2 px-2 py-1 bg-white/20 rounded text-sm font-bold">
                    +{achievement.xp_reward} XP
                </div>
            </div>
        </motion.div>
    );
}
