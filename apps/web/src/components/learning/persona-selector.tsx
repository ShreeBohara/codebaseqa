'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { Persona } from '@/lib/api-client';
import {
    Rocket, Shield, Layers, History,
    ChevronRight, Clock, BookOpen
} from 'lucide-react';

interface PersonaSelectorProps {
    personas: Persona[];
    onSelect: (persona: string) => void;
}

// Unique persona configurations with distinct styling
const PERSONA_CONFIG: Record<string, {
    icon: React.ReactNode;
    gradient: string;
    borderGradient: string;
    bgColor: string;
    title: string;
    topics: string[];
}> = {
    new_hire: {
        icon: <Rocket size={26} />,
        gradient: 'from-emerald-500 to-teal-500',
        borderGradient: 'from-emerald-400 to-teal-400',
        bgColor: 'bg-emerald-500',
        title: '🚀 The New Hire',
        topics: ['Quick Start', 'Environment Setup', 'Key Conventions', 'First PR']
    },
    auditor: {
        icon: <Shield size={26} />,
        gradient: 'from-rose-500 to-orange-500',
        borderGradient: 'from-rose-400 to-orange-400',
        bgColor: 'bg-rose-500',
        title: '🔐 Security Auditor',
        topics: ['Auth Flows', 'API Security', 'Data Validation', 'Vulnerabilities']
    },
    fullstack: {
        icon: <Layers size={26} />,
        gradient: 'from-violet-500 to-indigo-500',
        borderGradient: 'from-violet-400 to-indigo-400',
        bgColor: 'bg-violet-500',
        title: '⚡ Full Stack Developer',
        topics: ['Frontend Stack', 'Backend APIs', 'Database Layer', 'Deployment']
    },
    archaeologist: {
        icon: <History size={26} />,
        gradient: 'from-amber-500 to-yellow-500',
        borderGradient: 'from-amber-400 to-yellow-400',
        bgColor: 'bg-amber-500',
        title: '🏛️ The Archaeologist',
        topics: ['Legacy Code', 'Design History', 'Tech Debt', 'Evolution']
    }
};

export function PersonaSelector({ personas, onSelect }: PersonaSelectorProps) {
    const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

    return (
        <div className="w-full max-w-2xl mx-auto">
            {/* Header */}
            <motion.div
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-center mb-12"
            >
                <h1 className="text-3xl font-bold text-white mb-3">
                    Choose Your Learning Path
                </h1>
                <p className="text-slate-400 max-w-md mx-auto">
                    Select a persona to generate a personalized curriculum tailored to your goals
                </p>
            </motion.div>

            {/* Persona Cards - Vertical Stack */}
            <div className="space-y-4">
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
                            {/* Gradient Border Effect on Hover */}
                            <div className={`absolute -inset-0.5 rounded-2xl bg-gradient-to-r ${config.gradient} opacity-0 group-hover:opacity-100 transition-opacity duration-300 blur-sm`} />

                            {/* Card Content */}
                            <div className={`relative bg-slate-900 border border-slate-800 rounded-2xl p-5 transition-all duration-300 ${isHovered ? 'border-transparent bg-slate-900/95' : 'hover:border-slate-700'}`}>
                                <div className="flex items-start gap-4">
                                    {/* Icon with unique gradient */}
                                    <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${config.gradient} flex items-center justify-center text-white shadow-lg flex-shrink-0`}>
                                        {config.icon}
                                    </div>

                                    {/* Content */}
                                    <div className="flex-1 min-w-0">
                                        {/* TITLE - Now prominently displayed */}
                                        <h3 className={`text-lg font-bold mb-1 bg-gradient-to-r ${config.gradient} bg-clip-text text-transparent`}>
                                            {config.title}
                                        </h3>

                                        <p className="text-sm text-slate-400 mb-3 line-clamp-2">
                                            {persona.description}
                                        </p>

                                        {/* Unique Topics for each persona */}
                                        <div className="flex flex-wrap gap-2">
                                            {config.topics.map((topic, i) => (
                                                <span
                                                    key={i}
                                                    className={`text-xs px-2.5 py-1 rounded-full bg-gradient-to-r ${config.gradient} bg-opacity-10 text-white/80 border border-white/10`}
                                                >
                                                    {topic}
                                                </span>
                                            ))}
                                        </div>
                                    </div>

                                    {/* Arrow */}
                                    <motion.div
                                        animate={{ x: isHovered ? 4 : 0 }}
                                        className="text-slate-600 group-hover:text-white transition-colors flex-shrink-0 mt-2"
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
                                        <div className="flex items-center gap-4 text-slate-400">
                                            <span className="flex items-center gap-1.5">
                                                <BookOpen size={14} />
                                                6-8 lessons
                                            </span>
                                            <span className="flex items-center gap-1.5">
                                                <Clock size={14} />
                                                ~2 hours
                                            </span>
                                        </div>
                                        <span className={`font-semibold bg-gradient-to-r ${config.gradient} bg-clip-text text-transparent`}>
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
