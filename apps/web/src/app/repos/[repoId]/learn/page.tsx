'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { ArrowLeft, Folder, LayoutDashboard, Loader2, MessageSquare, Network, X } from 'lucide-react';
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
import { RepoContextBadge } from '@/components/common/repo-context-badge';
import { SiteFooter } from '@/components/common/site-footer';

interface LearnPageProps {
    params: Promise<{ repoId: string }>;
}

export default function LearnPage({ params }: LearnPageProps) {
    const [repoId, setRepoId] = useState<string>('');
    const [repoName, setRepoName] = useState<string>('');
    const [loading, setLoading] = useState(true);

    // State for learning flow
    const [personas, setPersonas] = useState<Persona[]>([]);
    const [syllabus, setSyllabus] = useState<Syllabus | null>(null);
    const [selectedPersona, setSelectedPersona] = useState<string | null>(null);
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
    const [currentLessonMeta, setCurrentLessonMeta] = useState<{ id: string; title: string; moduleId?: string } | null>(null);
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
            setRepoName(resolvedParams.repoId);

            try {
                const [repoData, personasData] = await Promise.all([
                    api.getRepo(resolvedParams.repoId),
                    api.getPersonas()
                ]);
                setRepoName(`${repoData.github_owner}/${repoData.github_name}`);
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
                api.getCompletedLessons(repoId, selectedPersona ?? undefined)
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

        setSelectedPersona(personaId);
        setGenerating(true);
        try {
            const [data, completedData] = await Promise.all([
                api.getSyllabus(repoId, personaId, { includeQualityMeta: true }),
                api.getCompletedLessons(repoId, personaId)
            ]);
            setSyllabus(data);
            setCompletedLessons(new Set(completedData));
        } catch (error) {
            console.error('Failed to generate syllabus:', error);
            alert('Failed to generate course. Please try again.');
        } finally {
            setGenerating(false);
        }
    };

    const handleLessonSelect = async (lesson: { id: string; title: string }, moduleId?: string) => {
        setLoadingLesson(true);
        try {
            const content = await api.generateLesson(repoId, lesson.id, lesson.title, {
                persona: selectedPersona ?? undefined,
                moduleId,
            });
            setCurrentLesson(content);
            setCurrentLessonMeta({ id: lesson.id, title: lesson.title, moduleId });
        } catch (error) {
            console.error('Failed to load lesson:', error);
            alert('Failed to load lesson content');
        } finally {
            setLoadingLesson(false);
        }
    };

    const handleRefreshTrack = async () => {
        if (!repoId || !selectedPersona) return;
        setGenerating(true);
        try {
            const [data, completedData] = await Promise.all([
                api.getSyllabus(repoId, selectedPersona, { refresh: true, includeQualityMeta: true }),
                api.getCompletedLessons(repoId, selectedPersona),
            ]);
            setSyllabus(data);
            setCompletedLessons(new Set(completedData));
        } catch (error) {
            console.error('Failed to refresh track:', error);
            alert('Failed to refresh track');
        } finally {
            setGenerating(false);
        }
    };

    const handleRegenerateLesson = async () => {
        if (!repoId || !currentLessonMeta) return;
        setLoadingLesson(true);
        try {
            const regenerated = await api.generateLesson(repoId, currentLessonMeta.id, currentLessonMeta.title, {
                persona: selectedPersona ?? undefined,
                moduleId: currentLessonMeta.moduleId,
                forceRegenerate: true,
            });
            setCurrentLesson(regenerated);
        } catch (error) {
            console.error('Failed to regenerate lesson:', error);
            alert('Failed to regenerate lesson');
        } finally {
            setLoadingLesson(false);
        }
    };

    if (loading) {
        return (
            <div className="h-screen bg-slate-950 flex items-center justify-center">
                <div className="text-center">
                    <Loader2 className="animate-spin text-slate-400 mx-auto mb-4" size={32} />
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
                                className="w-2.5 h-2.5 rounded-full bg-slate-500"
                                animate={{
                                    y: [0, -8, 0],
                                    opacity: [0.35, 0.9, 0.35]
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

    const isGraphTab = activeTab === 'graph';
    const repoDisplayName = repoName || repoId;

    return (
        <div className="bg-slate-950 text-slate-200">
            <div className="min-h-screen">
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
                        repoName={repoDisplayName}
                        content={currentLesson}
                        persona={selectedPersona ?? undefined}
                        moduleId={currentLessonMeta?.moduleId}
                        onRegenerate={handleRegenerateLesson}
                        onClose={() => {
                            setCurrentLesson(null);
                            setCurrentLessonMeta(null);
                        }}
                        onComplete={(xpGain) => {
                            // Immediately update completed lessons locally
                            setCompletedLessons(prev => new Set([...prev, currentLesson.id]));
                            handleGamificationUpdate(xpGain);
                        }}
                        onGamificationUpdate={handleGamificationUpdate}
                    />
                )}

                {/* Clean Header */}
                <header className="sticky top-0 z-20 border-b border-slate-800 bg-slate-950/95 backdrop-blur-md">
                    <div className={`${isGraphTab ? 'w-full px-4 py-3 md:px-6' : 'mx-auto max-w-5xl px-6 py-4'} flex items-center justify-between`}>
                        {/* Back Button - only show when on persona selection */}
                        <div className="flex min-w-0 items-center gap-3">
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
                                    onClick={() => {
                                        setSyllabus(null);
                                        setSelectedPersona(null);
                                        setCompletedLessons(new Set());
                                    }}
                                    className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors"
                                >
                                    <ArrowLeft size={18} />
                                    <span className="text-sm font-medium">Change Path</span>
                                </button>
                            )}
                            {repoDisplayName && (
                                <RepoContextBadge
                                    repoName={repoDisplayName}
                                    compact
                                    className="hidden max-w-[320px] border-slate-700/80 bg-slate-900/90 md:inline-flex"
                                />
                            )}
                        </div>

                        {/* Clean Tab Switcher */}
                        <div className="flex bg-slate-900/70 rounded-xl p-1 border border-slate-800">
                            <button
                                onClick={() => setActiveTab('dashboard')}
                                className={`flex items-center gap-1.5 px-4 py-1.5 rounded-md text-sm font-medium transition-all ${activeTab === 'dashboard'
                                    ? 'bg-slate-800 text-slate-100 border border-slate-700'
                                    : 'text-slate-400 hover:text-slate-200'
                                    }`}
                            >
                                <LayoutDashboard size={14} />
                                Dashboard
                            </button>
                            <button
                                onClick={() => setActiveTab('syllabus')}
                                className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${activeTab === 'syllabus'
                                    ? 'bg-slate-800 text-slate-100 border border-slate-700'
                                    : 'text-slate-400 hover:text-slate-200'
                                    }`}
                            >
                                Syllabus
                            </button>
                            <button
                                onClick={() => setActiveTab('graph')}
                                className={`flex items-center gap-1.5 px-4 py-1.5 rounded-md text-sm font-medium transition-all ${activeTab === 'graph'
                                    ? 'bg-slate-800 text-slate-100 border border-slate-700'
                                    : 'text-slate-400 hover:text-slate-200'
                                    }`}
                            >
                                <Network size={14} />
                                Graph
                            </button>
                        </div>

                        <div className="flex items-center gap-2">
                            <Link
                                href="/repos"
                                className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900/80 px-3 py-1.5 text-sm font-medium text-slate-200 transition-colors hover:bg-slate-800 hover:text-white"
                            >
                                <Folder size={14} />
                                <span className="hidden sm:inline">Repositories</span>
                            </Link>
                            <Link
                                href={`/repos/${repoId}/chat`}
                                className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900/80 px-3 py-1.5 text-sm font-medium text-slate-200 transition-colors hover:bg-slate-800 hover:text-white"
                            >
                                <MessageSquare size={14} />
                                <span className="hidden sm:inline">Chat</span>
                            </Link>
                        </div>
                    </div>
                </header>

                {isGraphTab ? (
                    <main className="h-[calc(100vh-82px)] min-h-[640px] w-full border-b border-slate-800 bg-slate-900/20">
                        <div className="h-full w-full">
                            <GraphView repoId={repoId} repoName={repoDisplayName} />
                        </div>
                    </main>
                ) : (
                    <main className="mx-auto max-w-5xl px-6 py-12">
                        {activeTab === 'dashboard' && userStats ? (
                            <DashboardView
                                stats={userStats}
                                achievements={achievements}
                                activity={activity}
                            />
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
                                        repoName={repoDisplayName}
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
                                        selectedPersona={selectedPersona ?? undefined}
                                        completedLessons={completedLessons}
                                        onRefreshTrack={handleRefreshTrack}
                                        onLessonSelect={handleLessonSelect}
                                    />
                                </motion.div>
                            )}
                        </AnimatePresence>
                        )}
                    </main>
                )}
            </div>
            <SiteFooter className={isGraphTab ? 'hidden' : undefined} />
        </div>
    );
}
