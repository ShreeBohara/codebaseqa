'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, LayoutDashboard, Loader2, Network, X } from 'lucide-react';
import { api, Persona, Syllabus, LessonContent, UserStats, Achievement } from '@/lib/api-client';
import { PersonaSelector } from '@/components/learning/persona-selector';
import { SyllabusView } from '@/components/learning/syllabus-view';
import { LessonView } from '@/components/learning/lesson-view';
import { GraphView } from '@/components/learning/graph-view';
import { XPWidget } from '@/components/learning/XPWidget';
import { AchievementsPanel, AchievementToast } from '@/components/learning/AchievementsPanel';
import { XPGainPopup } from '@/components/learning/XPBar';
import { DashboardView } from '@/components/dashboard/dashboard-view';
import { DemoBanner } from '@/components/common/demo-banner';

interface LearnPageProps {
    params: Promise<{ repoId: string }>;
}

export default function LearnPage({ params }: LearnPageProps) {
    const [repoId, setRepoId] = useState<string>('');
    const [loading, setLoading] = useState(true);

    // State for learning flow
    const [personas, setPersonas] = useState<Persona[]>([]);
    const [syllabus, setSyllabus] = useState<Syllabus | null>(null);
    const [generating, setGenerating] = useState(false);
    const [activeTab, setActiveTab] = useState<'syllabus' | 'graph' | 'dashboard'>('syllabus');

    useEffect(() => {
        const urlParams = new URLSearchParams(window.location.search);
        const tab = urlParams.get('tab');
        if (tab === 'graph') {
            setActiveTab('graph');
        }
    }, []);

    // Lesson State
    const [currentLesson, setCurrentLesson] = useState<LessonContent | null>(null);
    const [loadingLesson, setLoadingLesson] = useState(false);

    // Gamification State
    const [userStats, setUserStats] = useState<UserStats | null>(null);
    const [achievements, setAchievements] = useState<Achievement[]>([]);
    const [activity, setActivity] = useState<Record<string, number>>({});
    const [completedLessons, setCompletedLessons] = useState<Set<string>>(new Set());
    const [showAchievements, setShowAchievements] = useState(false);
    const [xpPopup, setXpPopup] = useState<{ amount: number; bonus?: number } | null>(null);
    const [newAchievement, setNewAchievement] = useState<{ name: string; icon: string; xp_reward: number } | null>(null);

    useEffect(() => {
        async function init() {
            const resolvedParams = await params;
            setRepoId(resolvedParams.repoId);

            try {
                const [, personasData] = await Promise.all([
                    api.getRepo(resolvedParams.repoId),
                    api.getPersonas()
                ]);
                setPersonas(personasData);

                // Load gamification data
                try {
                    const [stats, achievementsData, activityData, completedData] = await Promise.all([
                        api.getUserStats(resolvedParams.repoId),
                        api.getAchievements(resolvedParams.repoId),
                        api.getUserActivity(resolvedParams.repoId),
                        api.getCompletedLessons(resolvedParams.repoId)
                    ]);
                    setUserStats(stats);
                    setAchievements(achievementsData);
                    setActivity(activityData);
                    setCompletedLessons(new Set(completedData));
                } catch {
                    console.log('Gamification data not available yet');
                }
            } catch (error) {
                console.error('Failed to load learn page:', error);
            } finally {
                setLoading(false);
            }
        }
        init();
    }, [params]);

    const refreshStats = async () => {
        if (!repoId) return;
        try {
            const [stats, achievementsData, activityData, completedData] = await Promise.all([
                api.getUserStats(repoId),
                api.getAchievements(repoId),
                api.getUserActivity(repoId),
                api.getCompletedLessons(repoId)
            ]);
            setUserStats(stats);
            setAchievements(achievementsData);
            setActivity(activityData);
            setCompletedLessons(new Set(completedData));
        } catch {
            console.log('Failed to refresh stats');
        }
    };

    const handleGamificationUpdate = (xpGain: { amount: number; bonus?: number }) => {
        if (xpGain.amount > 0 || (xpGain.bonus ?? 0) > 0) {
            setXpPopup({ amount: xpGain.amount, bonus: xpGain.bonus });
        }
        refreshStats();
    };

    const handleSelectPersona = async (personaId: string) => {
        if (!repoId) return;

        setGenerating(true);
        try {
            const data = await api.generateSyllabus(repoId, personaId);
            setSyllabus(data);
        } catch (error) {
            console.error('Failed to generate syllabus:', error);
            alert('Failed to generate course. Please try again.');
        } finally {
            setGenerating(false);
        }
    };

    const handleLessonSelect = async (lesson: { id: string; title: string }) => {
        setLoadingLesson(true);
        try {
            const content = await api.generateLesson(repoId, lesson.id, lesson.title);
            setCurrentLesson(content);
        } catch (error) {
            console.error('Failed to load lesson:', error);
            alert('Failed to load lesson content');
        } finally {
            setLoadingLesson(false);
        }
    };

    if (loading) {
        return (
            <div className="h-screen bg-slate-950 flex items-center justify-center">
                <div className="text-center">
                    <Loader2 className="animate-spin text-indigo-500 mx-auto mb-4" size={32} />
                    <p className="text-slate-400">Loading learning path...</p>
                </div>
            </div>
        );
    }

    // Show loading overlay when generating
    if (generating || loadingLesson) {
        return (
            <div className="fixed inset-0 z-50 bg-slate-950 flex items-center justify-center">
                <motion.div
                    initial={{ scale: 0.9, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    className="flex flex-col items-center text-center"
                >
                    {/* Clean Loading Animation */}
                    <div className="flex gap-2 mb-8">
                        {[0, 1, 2].map((i) => (
                            <motion.div
                                key={i}
                                className="w-3 h-3 rounded-full bg-gradient-to-r from-indigo-500 to-purple-500"
                                animate={{
                                    y: [0, -12, 0],
                                    opacity: [0.5, 1, 0.5]
                                }}
                                transition={{
                                    duration: 0.8,
                                    repeat: Infinity,
                                    delay: i * 0.15
                                }}
                            />
                        ))}
                    </div>
                    <h3 className="text-xl font-semibold text-white mb-2">
                        {generating ? 'Designing Your Curriculum...' : 'Preparing Your Lesson...'}
                    </h3>
                    <p className="text-slate-400 text-sm max-w-sm">
                        {generating
                            ? 'AI is analyzing the codebase and creating a personalized learning path'
                            : 'Analyzing code context and generating interactive content'
                        }
                    </p>
                </motion.div>
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-slate-950 text-slate-200">
            <DemoBanner />
            {/* XP Gain Popup */}
            <AnimatePresence>
                {xpPopup && (
                    <XPGainPopup
                        amount={xpPopup.amount}
                        bonus={xpPopup.bonus}
                        onComplete={() => setXpPopup(null)}
                    />
                )}
            </AnimatePresence>

            {/* Achievement Unlock Toast */}
            <AnimatePresence>
                {newAchievement && (
                    <AchievementToast
                        achievement={newAchievement}
                        onComplete={() => setNewAchievement(null)}
                    />
                )}
            </AnimatePresence>

            {/* Achievements Modal */}
            <AnimatePresence>
                {showAchievements && (
                    <motion.div
                        className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        exit={{ opacity: 0 }}
                        onClick={() => setShowAchievements(false)}
                    >
                        <motion.div
                            initial={{ scale: 0.9, opacity: 0 }}
                            animate={{ scale: 1, opacity: 1 }}
                            exit={{ scale: 0.9, opacity: 0 }}
                            onClick={(e) => e.stopPropagation()}
                            className="relative"
                        >
                            <button
                                onClick={() => setShowAchievements(false)}
                                className="absolute -top-2 -right-2 p-2 bg-slate-800 rounded-full text-slate-400 hover:text-white transition-colors z-10"
                            >
                                <X size={16} />
                            </button>
                            <AchievementsPanel achievements={achievements} />
                        </motion.div>
                    </motion.div>
                )}
            </AnimatePresence>

            {/* Floating XP Widget */}
            <XPWidget
                stats={userStats}
                onOpenAchievements={() => setShowAchievements(true)}
            />

            {currentLesson && (
                <LessonView
                    repoId={repoId}
                    content={currentLesson}
                    onClose={() => setCurrentLesson(null)}
                    onComplete={(xpGain) => {
                        // Immediately update completed lessons locally
                        setCompletedLessons(prev => new Set([...prev, currentLesson.id]));
                        handleGamificationUpdate(xpGain);
                    }}
                    onGamificationUpdate={handleGamificationUpdate}
                />
            )}

            {/* Clean Header */}
            <header className="border-b border-slate-800/50 bg-slate-950/80 backdrop-blur-xl sticky top-0 z-20">
                <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
                    {/* Back Button - only show when on persona selection */}
                    {!syllabus ? (
                        <Link
                            href="/repos"
                            className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors"
                        >
                            <ArrowLeft size={18} />
                            <span className="text-sm font-medium">Back</span>
                        </Link>
                    ) : (
                        <button
                            onClick={() => setSyllabus(null)}
                            className="flex items-center gap-2 text-slate-400 hover:text-indigo-400 transition-colors"
                        >
                            <ArrowLeft size={18} />
                            <span className="text-sm font-medium">Change Path</span>
                        </button>
                    )}

                    {/* Clean Tab Switcher */}
                    <div className="flex bg-slate-800/50 rounded-lg p-1 border border-slate-700/50">
                        <button
                            onClick={() => setActiveTab('dashboard')}
                            className={`flex items-center gap-1.5 px-4 py-1.5 rounded-md text-sm font-medium transition-all ${activeTab === 'dashboard'
                                ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                                : 'text-slate-400 hover:text-slate-200'
                                }`}
                        >
                            <LayoutDashboard size={14} />
                            Dashboard
                        </button>
                        <div className="w-px bg-slate-700/50 my-1 mx-1" />
                        <button
                            onClick={() => setActiveTab('syllabus')}
                            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${activeTab === 'syllabus'
                                ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                                : 'text-slate-400 hover:text-slate-200'
                                }`}
                        >
                            Syllabus
                        </button>
                        <button
                            onClick={() => setActiveTab('graph')}
                            className={`flex items-center gap-1.5 px-4 py-1.5 rounded-md text-sm font-medium transition-all ${activeTab === 'graph'
                                ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                                : 'text-slate-400 hover:text-slate-200'
                                }`}
                        >
                            <Network size={14} />
                            Graph
                        </button>
                    </div>

                    {/* Spacer for balance */}
                    <div className="w-16" />
                </div>
            </header>

            <main className="max-w-5xl mx-auto px-6 py-12">
                {activeTab === 'dashboard' && userStats ? (
                    <DashboardView
                        stats={userStats}
                        achievements={achievements}
                        activity={activity}
                    />
                ) : activeTab === 'graph' ? (
                    <div className="h-[calc(100vh-160px)] min-h-[600px] border border-slate-800 rounded-2xl overflow-hidden bg-slate-900/30">
                        <GraphView repoId={repoId} />
                    </div>
                ) : (
                    <AnimatePresence mode="wait">
                        {!syllabus ? (
                            <motion.div
                                key="selection"
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0, y: -20 }}
                            >
                                <PersonaSelector
                                    personas={personas}
                                    onSelect={handleSelectPersona}
                                />
                            </motion.div>
                        ) : (
                            <motion.div
                                key="syllabus"
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                            >
                                <SyllabusView
                                    syllabus={syllabus}
                                    completedLessons={completedLessons}
                                    onLessonSelect={handleLessonSelect}
                                />
                            </motion.div>
                        )}
                    </AnimatePresence>
                )}
            </main>
        </div>
    );
}
