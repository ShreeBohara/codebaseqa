'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Persona } from '@/lib/api-client';
import { RepoContextBadge } from '@/components/common/repo-context-badge';
import {
    Rocket, Shield, Layers, History,
    ChevronRight, Clock, BookOpen, Target, FileCheck2
} from 'lucide-react';

interface PersonaSelectorProps {
    personas: Persona[];
    onSelect: (persona: string) => void;
    repoName?: string;
}

// Unique persona configurations with distinct styling
const PERSONA_CONFIG: Record<string, {
    icon: React.ReactNode;
    iconTone: string;
    dotTone: string;
    title: string;
    mastery: string;
    topics: string[];
    outputs: string[];
}> = {
    new_hire: {
        icon: <Rocket size={26} />,
        iconTone: 'text-emerald-300 bg-emerald-500/10 border-emerald-500/30',
        dotTone: 'bg-emerald-300',
        title: 'The New Hire',
        mastery: 'Become productive in this repo with safe first-shipment confidence.',
        topics: ['Quick Start', 'Environment Setup', 'Key Conventions', 'First PR'],
        outputs: ['Onboarding checklist', 'First-change map']
    },
    auditor: {
        icon: <Shield size={26} />,
        iconTone: 'text-rose-300 bg-rose-500/10 border-rose-500/30',
        dotTone: 'bg-rose-300',
        title: 'Security Auditor',
        mastery: 'Audit trust boundaries with evidence-backed risk prioritization.',
        topics: ['Auth Flows', 'API Security', 'Data Validation', 'Vulnerabilities'],
        outputs: ['Risk hotspot matrix', 'Control-gap report']
    },
    fullstack: {
        icon: <Layers size={26} />,
        iconTone: 'text-indigo-300 bg-indigo-500/10 border-indigo-500/30',
        dotTone: 'bg-indigo-300',
        title: 'Full Stack Developer',
        mastery: 'Trace end-to-end feature behavior from UI to persistence.',
        topics: ['Frontend Stack', 'Backend APIs', 'Database Layer', 'Deployment'],
        outputs: ['Request-to-render flow', 'Contract dependency map']
    },
    archaeologist: {
        icon: <History size={26} />,
        iconTone: 'text-amber-300 bg-amber-500/10 border-amber-500/30',
        dotTone: 'bg-amber-300',
        title: 'The Archaeologist',
        mastery: 'Reconstruct design history and isolate debt-heavy hotspots.',
        topics: ['Legacy Code', 'Design History', 'Tech Debt', 'Evolution'],
        outputs: ['Legacy timeline', 'Debt containment plan']
    }
};

export function PersonaSelector({ personas, onSelect, repoName }: PersonaSelectorProps) {
    const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

    return (
        <div className="w-full max-w-2xl mx-auto">
            {/* Header */}
            <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-center mb-8"
            >
                <div className="inline-flex items-center gap-2 rounded-full border border-slate-700 bg-slate-900/80 px-3 py-1 text-xs text-slate-300 mb-4">
                    <Target size={12} />
                    Step 1: Choose Role
                </div>
                <h1 className="text-3xl font-semibold tracking-tight text-slate-100 mb-2">
                    Select Your Mission
                </h1>
                <p className="text-slate-400 max-w-md mx-auto">
                    Each role builds a different learning track with unique deliverables
                </p>
                {repoName && (
                    <div className="mt-4 flex justify-center">
                        <RepoContextBadge
                            repoName={repoName}
                            className="max-w-full border-slate-700/80 bg-slate-900/90"
                        />
                    </div>
                )}
            </motion.div>

            {/* Persona Cards - Vertical Stack */}
            <div className="space-y-3">
                {personas.map((persona, index) => {
                    const config = PERSONA_CONFIG[persona.id] || PERSONA_CONFIG.new_hire;
                    const isHovered = hoveredIndex === index;

                    return (
                        <motion.div
                            key={persona.id}
                            initial={{ opacity: 0, x: -20 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: index * 0.1 }}
                            onMouseEnter={() => setHoveredIndex(index)}
                            onMouseLeave={() => setHoveredIndex(null)}
                            onClick={() => onSelect(persona.id)}
                            className="relative group cursor-pointer"
                        >
                            {/* Card Content */}
                            <div className={`relative rounded-2xl border bg-slate-900/60 p-5 transition-colors duration-200 ${isHovered ? 'border-slate-600 bg-slate-900/85' : 'border-slate-800 hover:border-slate-700'}`}>
                                <div className="flex items-start gap-4">
                                    {/* Icon with subtle persona tint */}
                                    <div className={`h-12 w-12 rounded-xl border flex items-center justify-center flex-shrink-0 ${config.iconTone}`}>
                                        {config.icon}
                                    </div>

                                    {/* Content */}
                                    <div className="flex-1 min-w-0">
                                        <div className="flex items-center gap-2 mb-1">
                                            <span className={`h-1.5 w-1.5 rounded-full ${config.dotTone}`} />
                                            <h3 className="text-lg font-semibold text-slate-100">
                                                {config.title}
                                            </h3>
                                        </div>

                                        <p className="text-sm text-slate-400 mb-3 line-clamp-2">
                                            {persona.description}
                                        </p>
                                        <p className="text-xs text-slate-300 mb-3">
                                            {config.mastery}
                                        </p>

                                        {/* Unique Topics for each persona */}
                                        <div className="flex flex-wrap gap-2">
                                            {config.topics.map((topic, i) => (
                                                <span
                                                    key={i}
                                                    className="text-xs px-2.5 py-1 rounded-full border border-slate-700 bg-slate-800/70 text-slate-300"
                                                >
                                                    {topic}
                                                </span>
                                            ))}
                                        </div>
                                        <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
                                            {config.outputs.map((output, i) => (
                                                <div
                                                    key={i}
                                                    className="inline-flex items-center gap-2 rounded-lg border border-slate-700/80 bg-slate-950/60 px-2.5 py-1.5 text-xs text-slate-300"
                                                >
                                                    <FileCheck2 size={12} className="text-slate-400" />
                                                    {output}
                                                </div>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Arrow */}
                                    <motion.div
                                        animate={{ x: isHovered ? 4 : 0 }}
                                        className="text-slate-600 group-hover:text-slate-300 transition-colors flex-shrink-0 mt-2"
                                    >
                                        <ChevronRight size={24} />
                                    </motion.div>
                                </div>

                                {/* Hover Details */}
                                <motion.div
                                    initial={{ height: 0, opacity: 0 }}
                                    animate={{
                                        height: isHovered ? 'auto' : 0,
                                        opacity: isHovered ? 1 : 0
                                    }}
                                    className="overflow-hidden"
                                >
                                    <div className="pt-4 mt-4 border-t border-slate-800 flex items-center justify-between text-sm">
                                        <div className="flex items-center gap-4 text-slate-500">
                                            <span className="flex items-center gap-1.5">
                                                <BookOpen size={14} />
                                                6-8 lessons
                                            </span>
                                            <span className="flex items-center gap-1.5">
                                                <Clock size={14} />
                                                ~2 hours
                                            </span>
                                        </div>
                                        <span className="font-medium text-slate-200 inline-flex items-center gap-1.5">
                                            <BookOpen size={14} />
                                            Start Learning →
                                        </span>
                                    </div>
                                </motion.div>
                            </div>
                        </motion.div>
                    );
                })}
            </div>
        </div>
    );
}
