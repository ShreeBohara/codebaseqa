'use client';

import { useState } from 'react';
import { Syllabus, Lesson } from '@/lib/api-client';
import { motion, AnimatePresence } from 'framer-motion';
import {
    Clock, ChevronDown, RotateCw,
    Play, CheckCircle2, Circle, Target
} from 'lucide-react';

interface SyllabusViewProps {
    syllabus: Syllabus;
    selectedPersona?: string;
    onRefreshTrack?: () => Promise<void> | void;
    onLessonSelect: (lesson: Lesson, moduleId?: string) => void;
    completedLessons?: Set<string>;
}

export function SyllabusView({
    syllabus,
    selectedPersona,
    onRefreshTrack,
    onLessonSelect,
    completedLessons = new Set(),
}: SyllabusViewProps) {
    const [expandedModules, setExpandedModules] = useState<Set<number>>(new Set([0])); // First module expanded by default
    const [refreshing, setRefreshing] = useState(false);

    const handleRefresh = async () => {
        if (!onRefreshTrack || refreshing) return;
        setRefreshing(true);
        try {
            await onRefreshTrack();
        } finally {
            setRefreshing(false);
        }
    };

    const cacheLabel = syllabus.cache_info?.source === 'cache' ? 'Cached Track' : 'Freshly Generated';
    const expiresAt = syllabus.cache_info?.expires_at ? new Date(syllabus.cache_info.expires_at).toLocaleString() : null;

    const toggleModule = (index: number) => {
        setExpandedModules(prev => {
            const next = new Set(prev);
            if (next.has(index)) {
                next.delete(index);
            } else {
                next.add(index);
            }
            return next;
        });
    };

    return (
        <div className="w-full max-w-3xl mx-auto">
            {/* Header */}
            <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-center mb-10"
            >
                <div className="inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-900/80 px-3 py-1 text-xs text-slate-300 mb-4">
                    <Target size={12} />
                    Step 2: Track Map
                </div>
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-medium mb-4 uppercase tracking-wider">
                    {(selectedPersona || syllabus.persona).replace('_', ' ')} Track
                </div>

                <h1 className="text-2xl md:text-3xl font-bold text-white mb-3">
                    {syllabus.title}
                </h1>

                <p className="text-slate-400 text-sm max-w-xl mx-auto mb-8">
                    {syllabus.description}
                </p>

                <div className="mx-auto mb-6 flex max-w-2xl flex-col gap-4 rounded-2xl border border-slate-800 bg-slate-900/50 p-4 text-left sm:flex-row sm:items-center sm:justify-between">
                    <div>
                        <p className="text-xs uppercase tracking-wider text-slate-500">Track Status</p>
                        <p className="text-sm text-slate-200">{cacheLabel}</p>
                        {expiresAt && (
                            <p className="text-xs text-slate-500 mt-1">Refreshes by: {expiresAt}</p>
                        )}
                    </div>
                    <button
                        onClick={handleRefresh}
                        disabled={!onRefreshTrack || refreshing}
                        className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-200 transition-colors hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                        <RotateCw size={14} className={refreshing ? 'animate-spin' : ''} />
                        Regenerate Track
                    </button>
                </div>
            </motion.div>

            {/* Timeline Modules */}
            <div className="relative">
                {/* Timeline Line */}
                <div className="absolute left-5 top-0 bottom-0 w-px bg-gradient-to-b from-slate-700 via-slate-700 to-transparent" />

                <div className="space-y-4">
                    {syllabus.modules.map((module, mIdx) => {
                        const isExpanded = expandedModules.has(mIdx);
                        const moduleLessons = module.lessons;
                        const completedInModule = moduleLessons.filter(l => completedLessons.has(l.id)).length;
                        const isModuleComplete = completedInModule === moduleLessons.length && moduleLessons.length > 0;

                        return (
                            <motion.div
                                key={mIdx}
                                initial={{ opacity: 0, x: -10 }}
                                animate={{ opacity: 1, x: 0 }}
                                transition={{ delay: mIdx * 0.1 }}
                            >
                                {/* Module Header */}
                                <button
                                    onClick={() => toggleModule(mIdx)}
                                    className="w-full group"
                                >
                                    <div className="flex items-start gap-4">
                                        {/* Timeline Node */}
                                        <div className={`relative z-10 w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 border-2 transition-all ${isModuleComplete
                                                ? 'bg-emerald-500 border-emerald-400 text-white'
                                                : isExpanded
                                                    ? 'bg-indigo-500 border-indigo-400 text-white'
                                                    : 'bg-slate-900 border-slate-700 text-slate-400 group-hover:border-slate-500'
                                            }`}>
                                            {isModuleComplete ? (
                                                <CheckCircle2 size={18} />
                                            ) : (
                                                <span className="font-semibold text-sm">{mIdx + 1}</span>
                                            )}
                                        </div>

                                        {/* Module Card */}
                                        <div className={`flex-1 bg-slate-900/50 border rounded-xl p-4 text-left transition-all ${isExpanded
                                                ? 'border-slate-700 bg-slate-900/80'
                                                : 'border-slate-800 hover:border-slate-700'
                                            }`}>
                                            <div className="flex items-center justify-between">
                                                <div>
                                                    <h3 className="font-semibold text-white group-hover:text-indigo-300 transition-colors">
                                                        {module.title}
                                                    </h3>
                                                    <p className="text-sm text-slate-500 mt-0.5">
                                                        {completedInModule}/{moduleLessons.length} lessons
                                                        {isModuleComplete && <span className="text-emerald-400 ml-2">✓ Complete</span>}
                                                    </p>
                                                </div>
                                                <motion.div
                                                    animate={{ rotate: isExpanded ? 180 : 0 }}
                                                    className="text-slate-500"
                                                >
                                                    <ChevronDown size={20} />
                                                </motion.div>
                                            </div>
                                        </div>
                                    </div>
                                </button>

                                {/* Expanded Lessons */}
                                <AnimatePresence>
                                    {isExpanded && (
                                        <motion.div
                                            initial={{ opacity: 0, height: 0 }}
                                            animate={{ opacity: 1, height: 'auto' }}
                                            exit={{ opacity: 0, height: 0 }}
                                            transition={{ duration: 0.2 }}
                                            className="overflow-hidden"
                                        >
                                            <div className="ml-14 mt-2 space-y-1">
                                                {moduleLessons.map((lesson) => (
                                                    <LessonRow
                                                        key={lesson.id}
                                                        lesson={lesson}
                                                        isCompleted={completedLessons.has(lesson.id)}
                                                        onClick={() => onLessonSelect(lesson, `module-${mIdx + 1}`)}
                                                    />
                                                ))}
                                            </div>
                                        </motion.div>
                                    )}
                                </AnimatePresence>
                            </motion.div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}

interface LessonRowProps {
    lesson: Lesson;
    isCompleted: boolean;
    onClick: () => void;
}

function LessonRow({ lesson, isCompleted, onClick }: LessonRowProps) {
    const [isHovered, setIsHovered] = useState(false);

    return (
        <motion.button
            onClick={onClick}
            onMouseEnter={() => setIsHovered(true)}
            onMouseLeave={() => setIsHovered(false)}
            whileHover={{ x: 4 }}
            className={`w-full text-left p-3 rounded-lg transition-all flex items-center gap-3 group ${isCompleted
                    ? 'bg-emerald-500/5 hover:bg-emerald-500/10'
                    : 'hover:bg-slate-800/50'
                }`}
        >
            {/* Status Circle */}
            <div className={`w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0 ${isCompleted
                    ? 'text-emerald-400'
                    : 'text-slate-600 group-hover:text-indigo-400'
                }`}>
                {isCompleted ? <CheckCircle2 size={18} /> : <Circle size={16} />}
            </div>

            {/* Content */}
            <div className="flex-1 min-w-0">
                <h4 className={`text-sm font-medium truncate transition-colors ${isCompleted
                        ? 'text-emerald-300'
                        : 'text-slate-300 group-hover:text-white'
                    }`}>
                    {lesson.title}
                </h4>
            </div>

            {/* Meta */}
            <div className="flex items-center gap-3 text-xs text-slate-500 flex-shrink-0">
                <span className="flex items-center gap-1">
                    <Clock size={12} />
                    {lesson.estimated_minutes}m
                </span>

                <motion.div
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{
                        opacity: isHovered ? 1 : 0,
                        scale: isHovered ? 1 : 0.8
                    }}
                    className={`p-1.5 rounded-lg ${isCompleted
                            ? 'bg-emerald-500/20 text-emerald-400'
                            : 'bg-indigo-500/20 text-indigo-400'
                        }`}
                >
                    <Play size={12} fill="currentColor" />
                </motion.div>
            </div>
        </motion.button>
    );
}
