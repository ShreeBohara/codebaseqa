'use client';

import { motion } from 'framer-motion';
import { UserStats, Achievement } from '@/lib/api-client';
import { ActivityHeatmap } from './activity-heatmap';
import { AchievementsPanel } from '../learning/AchievementsPanel';
import { Trophy, Flame, Target, BookOpen, Star } from 'lucide-react';

interface DashboardViewProps {
    stats: UserStats;
    achievements: Achievement[];
    activity: Record<string, number>;
}

export function DashboardView({ stats, achievements, activity }: DashboardViewProps) {
    // Calculate unlock progress
    const unlockedCount = achievements.filter(a => a.unlocked).length;
    const progress = Math.round((unlockedCount / achievements.length) * 100) || 0;

    return (
        <div className="space-y-6 animate-in fade-in duration-500">
            {/* Top Grid: Overview Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <DashboardCard
                    icon={<Star className="text-yellow-400" />}
                    label="Current Level"
                    value={stats.level.level.toString()}
                    subValue={stats.level.title}
                    gradient="from-yellow-500/10 to-amber-500/10"
                />
                <DashboardCard
                    icon={<ZapIcon />}
                    label="Total XP"
                    value={stats.total_xp.toLocaleString()}
                    subValue={`${Math.round(stats.level.xp_progress * 100)}% to next`}
                    gradient="from-indigo-500/10 to-purple-500/10"
                />
                <DashboardCard
                    icon={<Flame className="text-orange-500" />}
                    label="Day Streak"
                    value={stats.streak.current.toString()}
                    subValue={`Longest: ${stats.streak.longest}`}
                    gradient="from-orange-500/10 to-red-500/10"
                />
                <DashboardCard
                    icon={<Trophy className="text-purple-400" />}
                    label="Achievements"
                    value={`${unlockedCount}/${achievements.length}`}
                    subValue={`${progress}% Complete`}
                    gradient="from-emerald-500/10 to-teal-500/10"
                />
            </div>

            {/* Middle Row: Heatmap & Level Progress */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2">
                    <ActivityHeatmap data={activity} />
                </div>

                {/* Level Progress Detail */}
                <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-6 relative overflow-hidden">
                    <div className="relative z-10">
                        <h3 className="text-lg font-semibold text-white mb-4">Level Progress</h3>
                        <div className="flex items-center gap-4 mb-6">
                            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center text-3xl shadow-lg shadow-purple-500/20">
                                {stats.level.icon}
                            </div>
                            <div>
                                <div className="text-2xl font-bold text-white">{stats.level.title}</div>
                                <div className="text-zinc-400">Level {stats.level.level}</div>
                            </div>
                        </div>

                        <div className="space-y-2">
                            <div className="flex justify-between text-sm">
                                <span className="text-zinc-400">XP Progress</span>
                                <span className="text-white font-medium">{stats.total_xp} / {stats.level.xp_for_next_level} XP</span>
                            </div>
                            <div className="h-4 bg-zinc-800 rounded-full overflow-hidden p-0.5">
                                <motion.div
                                    initial={{ width: 0 }}
                                    animate={{ width: `${stats.level.xp_progress * 100}%` }}
                                    transition={{ duration: 1, ease: "easeOut" }}
                                    className="h-full rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 shadow-[0_0_10px_rgba(168,85,247,0.4)]"
                                />
                            </div>
                            <p className="text-xs text-zinc-500 text-right mt-1">
                                {stats.level.xp_for_next_level - stats.total_xp} XP to next level
                            </p>
                        </div>
                    </div>

                    {/* Background decoration */}
                    <div className="absolute -right-10 -bottom-10 w-64 h-64 bg-indigo-500/5 rounded-full blur-3xl pointer-events-none" />
                </div>
            </div>

            {/* Bottom Row: Detailed Stats & Achievements */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Stat Breakdown */}
                <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-6">
                    <h3 className="text-lg font-semibold text-white mb-4">Statistics</h3>
                    <div className="space-y-4">
                        <StatRow label="Lessons Completed" value={stats.lessons_completed} icon={<BookOpen size={16} className="text-blue-400" />} />
                        <StatRow label="Quizzes Passed" value={stats.quizzes_passed} icon={<Target size={16} className="text-green-400" />} />
                        <StatRow label="Perfect Quizzes" value={stats.perfect_quizzes} icon={<Star size={16} className="text-yellow-400" />} />
                        <StatRow label="Challenges Solved" value={stats.challenges_completed} icon={<Trophy size={16} className="text-purple-400" />} />
                    </div>
                </div>

                {/* Achievements List */}
                <div className="lg:col-span-2">
                    {/* Reuse the existing panel style implicitly via container */}
                    <AchievementsPanel achievements={achievements} />
                </div>
            </div>
        </div>
    );
}

interface DashboardCardProps {
    icon: React.ReactNode;
    label: string;
    value: string | number;
    subValue?: string;
    gradient: string;
}

function DashboardCard({ icon, label, value, subValue, gradient }: DashboardCardProps) {
    return (
        <div className={`rounded-2xl p-5 border border-zinc-800 bg-gradient-to-br ${gradient} bg-zinc-900/30`}>
            <div className="flex items-start justify-between mb-4">
                <div className="p-2 bg-zinc-900/50 rounded-lg border border-zinc-800/50 text-white">
                    {icon}
                </div>
                {subValue && <span className="text-xs font-medium text-zinc-500 bg-zinc-900/50 px-2 py-1 rounded-full border border-zinc-800/50">{subValue}</span>}
            </div>
            <div>
                <div className="text-zinc-400 text-sm font-medium mb-1">{label}</div>
                <div className="text-2xl font-bold text-white tracking-tight">{value}</div>
            </div>
        </div>
    );
}

interface StatRowProps {
    label: string;
    value: string | number;
    icon: React.ReactNode;
}

function StatRow({ label, value, icon }: StatRowProps) {
    return (
        <div className="flex items-center justify-between p-3 rounded-xl bg-zinc-800/30 border border-zinc-800/50">
            <div className="flex items-center gap-3">
                <div className="p-1.5 bg-zinc-900 rounded-lg">
                    {icon}
                </div>
                <span className="text-zinc-300 text-sm">{label}</span>
            </div>
            <span className="font-bold text-white">{value}</span>
        </div>
    );
}

function ZapIcon({ className }: { className?: string }) {
    return (
        <svg
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className={`text-indigo-400 ${className}`}
        >
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
        </svg>
    )
}
