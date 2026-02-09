'use client';

import { motion } from 'framer-motion';
import {
    ArrowUpRight,
    Braces,
    CheckCircle2,
    Database,
    Flame,
    GraduationCap,
    Layers3,
    Network,
    ServerCog,
    Trophy,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { type ReactNode, type WheelEvent } from 'react';

const ROLE_PATHS = [
    'New Hire Onboarding',
    'Full-Stack Development',
    'Security Auditing',
    'Senior Architecture',
    'Platform Engineering',
    'DevOps Enablement',
    'Team Lead Ramp-Up',
];

type GraphAccent = 'sky' | 'indigo' | 'emerald' | 'violet' | 'cyan';

type GraphNode = {
    label: string;
    detail: string;
    x: number;
    y: number;
    icon: LucideIcon;
    accent: GraphAccent;
};

const GRAPH_NODES: GraphNode[] = [
    { label: 'UI Layer', detail: 'React', x: 18, y: 32, icon: Braces, accent: 'sky' },
    { label: 'Auth', detail: 'JWT + RBAC', x: 24, y: 74, icon: ServerCog, accent: 'cyan' },
    { label: 'API', detail: 'REST Routes', x: 78, y: 30, icon: Network, accent: 'indigo' },
    { label: 'Storage', detail: 'Postgres', x: 82, y: 70, icon: Database, accent: 'emerald' },
    { label: 'Workers', detail: 'Jobs', x: 50, y: 16, icon: Layers3, accent: 'violet' },
];

const NODE_ACCENTS: Record<GraphAccent, { bubble: string; iconWrap: string; icon: string }> = {
    sky: {
        bubble: 'border-sky-400/40 bg-sky-500/15 text-sky-100',
        iconWrap: 'bg-sky-400/20',
        icon: 'text-sky-200',
    },
    indigo: {
        bubble: 'border-indigo-400/40 bg-indigo-500/15 text-indigo-100',
        iconWrap: 'bg-indigo-400/20',
        icon: 'text-indigo-200',
    },
    emerald: {
        bubble: 'border-emerald-400/40 bg-emerald-500/15 text-emerald-100',
        iconWrap: 'bg-emerald-400/20',
        icon: 'text-emerald-200',
    },
    violet: {
        bubble: 'border-violet-400/40 bg-violet-500/15 text-violet-100',
        iconWrap: 'bg-violet-400/20',
        icon: 'text-violet-200',
    },
    cyan: {
        bubble: 'border-cyan-400/40 bg-cyan-500/15 text-cyan-100',
        iconWrap: 'bg-cyan-400/20',
        icon: 'text-cyan-200',
    },
};

const GRAPH_STATS = [
    { value: '42', label: 'Components' },
    { value: '87', label: 'API Calls' },
    { value: '15', label: 'DB Tables' },
    { value: '4', label: 'Bounded Contexts' },
];

const MODULE_PROGRESS = [
    { label: 'Architecture', progress: 92, tone: 'from-violet-400 to-indigo-400' },
    { label: 'Auth Flow', progress: 74, tone: 'from-indigo-400 to-blue-400' },
    { label: 'Data Layer', progress: 58, tone: 'from-cyan-400 to-teal-400' },
];

// Card container with shared motion and hover treatment.
function BentoCard({
    children,
    className,
    delay = 0,
    onWheelCapture,
}: {
    children: ReactNode;
    className?: string;
    delay?: number;
    onWheelCapture?: (event: WheelEvent<HTMLDivElement>) => void;
}) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay }}
            whileHover={{ y: -3 }}
            onWheelCapture={onWheelCapture}
            className={`bg-zinc-900/45 border border-white/5 p-6 rounded-3xl backdrop-blur-sm overflow-hidden relative group hover:border-white/15 transition-colors ${className}`}
        >
            <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_15%_15%,rgba(99,102,241,0.08),transparent_40%)] opacity-0 transition-opacity duration-500 group-hover:opacity-100" />
            {children}
        </motion.div>
    );
}

export function BentoGrid() {
    const handleScrollableCardWheel = (event: WheelEvent<HTMLDivElement>) => {
        const card = event.currentTarget;
        const maxScrollTop = card.scrollHeight - card.clientHeight;

        if (maxScrollTop <= 0) {
            return;
        }

        // Fully capture wheel events so page scrolling does not hijack the card.
        event.preventDefault();
        event.stopPropagation();

        const nextScrollTop = card.scrollTop + event.deltaY;
        card.scrollTop = Math.max(0, Math.min(maxScrollTop, nextScrollTop));
    };

    return (
        <section className="max-w-6xl mx-auto px-6 py-24">
            <div className="mb-16 text-center">
                <h2 className="text-3xl md:text-5xl font-bold bg-clip-text text-transparent bg-gradient-to-b from-white to-white/60 mb-4">
                    More than just a chatbot.
                </h2>
                <p className="text-zinc-400 text-lg max-w-2xl mx-auto">
                    Deep understanding requires more than text. Visualize structure, track progress, and test your knowledge.
                </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-6 md:grid-rows-2 gap-4 h-auto md:h-[640px]">
                {/* 1. Visualizer Card (Large Left) */}
                <BentoCard className="md:col-span-4 md:row-span-2 relative flex flex-col justify-between overflow-hidden">
                    <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-indigo-500/15 rounded-full blur-[90px] -translate-y-1/2 translate-x-1/2 pointer-events-none" />
                    <div className="absolute bottom-0 left-0 w-[360px] h-[360px] bg-cyan-400/10 rounded-full blur-[90px] translate-y-1/3 -translate-x-1/3 pointer-events-none" />

                    <div className="relative z-10">
                        <div className="mb-5 flex flex-wrap items-center gap-2 text-xs">
                            <span className="inline-flex items-center gap-1 rounded-full border border-emerald-400/30 bg-emerald-500/10 px-3 py-1 text-emerald-300">
                                <span className="h-1.5 w-1.5 rounded-full bg-emerald-300 animate-pulse" />
                                Live analysis
                            </span>
                            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-zinc-300">
                                Monorepo mode
                            </span>
                            <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-zinc-300">
                                9 language parsers
                            </span>
                        </div>

                        <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 flex items-center justify-center mb-4 border border-indigo-500/20">
                            <Network className="text-indigo-400" />
                        </div>

                        <div className="mb-2 flex items-start justify-between gap-4">
                            <h3 className="text-2xl font-semibold text-white">Interactive Dependency Graph</h3>
                            <span className="hidden md:inline-flex items-center gap-1 rounded-lg border border-indigo-400/30 bg-indigo-500/10 px-2.5 py-1 text-xs font-medium text-indigo-200">
                                Inspect map
                                <ArrowUpRight size={14} />
                            </span>
                        </div>

                        <p className="text-zinc-300 max-w-xl leading-relaxed">
                            Don&apos;t just read code, map the system. Explore ownership boundaries, API traffic, and data flow with contextual nodes that mirror your real architecture.
                        </p>

                        <div className="mt-4 flex flex-wrap gap-2">
                            {['Service Boundaries', 'Hotspot Discovery', 'Schema Relationships'].map((item) => (
                                <span key={item} className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-zinc-300">
                                    {item}
                                </span>
                            ))}
                        </div>
                    </div>

                    <div className="mt-8 flex-1 min-h-[320px] w-full rounded-2xl border border-white/10 bg-zinc-950/70 p-5 md:p-6 relative overflow-hidden group-hover:border-indigo-400/30 transition-colors">
                        <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(56,189,248,0.14),transparent_45%),radial-gradient(circle_at_75%_40%,rgba(99,102,241,0.14),transparent_48%)] pointer-events-none" />

                        <motion.div
                            className="pointer-events-none absolute inset-y-0 -left-10 w-28 bg-gradient-to-r from-transparent via-indigo-300/20 to-transparent blur-xl"
                            initial={{ x: '-30%' }}
                            whileInView={{ x: '130%' }}
                            transition={{ duration: 4.4, repeat: Infinity, ease: 'linear' }}
                            viewport={{ once: true }}
                        />

                        <svg className="absolute inset-0 h-full w-full opacity-80" viewBox="0 0 100 100" preserveAspectRatio="none">
                            <defs>
                                <linearGradient id="edgeGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                                    <stop offset="0%" stopColor="rgba(125,211,252,0.8)" />
                                    <stop offset="100%" stopColor="rgba(129,140,248,0.35)" />
                                </linearGradient>
                            </defs>

                            <circle cx="50" cy="50" r="34" stroke="rgba(255,255,255,0.08)" strokeDasharray="2 1.6" fill="none" />

                            {GRAPH_NODES.map((node, index) => (
                                <motion.line
                                    key={node.label}
                                    x1="50"
                                    y1="50"
                                    x2={node.x}
                                    y2={node.y}
                                    stroke="url(#edgeGradient)"
                                    strokeWidth="0.4"
                                    initial={{ opacity: 0 }}
                                    whileInView={{ opacity: 0.95 }}
                                    viewport={{ once: true }}
                                    transition={{ duration: 0.8, delay: 0.2 + index * 0.08 }}
                                />
                            ))}
                        </svg>

                        {GRAPH_NODES.map((node, index) => {
                            const Icon = node.icon;
                            const accent = NODE_ACCENTS[node.accent];

                            return (
                                <motion.div
                                    key={node.label}
                                    className={`absolute z-20 -translate-x-1/2 -translate-y-1/2 rounded-xl border px-3 py-2 backdrop-blur-sm shadow-[0_0_35px_rgba(2,6,23,0.45)] ${accent.bubble}`}
                                    style={{ top: `${node.y}%`, left: `${node.x}%` }}
                                    initial={{ opacity: 0, scale: 0.75 }}
                                    whileInView={{ opacity: 1, scale: 1 }}
                                    viewport={{ once: true }}
                                    transition={{ duration: 0.4, delay: 0.22 + index * 0.08 }}
                                >
                                    <div className="flex items-center gap-2">
                                        <span className={`grid h-6 w-6 place-items-center rounded-lg ${accent.iconWrap}`}>
                                            <Icon size={14} className={accent.icon} />
                                        </span>
                                        <div>
                                            <p className="text-[11px] font-semibold leading-none">{node.label}</p>
                                            <p className="text-[10px] text-white/70 leading-none mt-1">{node.detail}</p>
                                        </div>
                                    </div>
                                </motion.div>
                            );
                        })}

                        <motion.div
                            className="absolute left-1/2 top-1/2 z-30 h-20 w-20 -translate-x-1/2 -translate-y-1/2 rounded-full border border-indigo-300/40 bg-indigo-500/30 backdrop-blur-sm grid place-items-center shadow-[0_0_45px_rgba(99,102,241,0.45)]"
                            initial={{ scale: 0.88, opacity: 0 }}
                            whileInView={{ scale: 1, opacity: 1 }}
                            transition={{ duration: 0.45 }}
                            viewport={{ once: true }}
                        >
                            <motion.span
                                className="absolute inset-0 rounded-full border border-indigo-300/30"
                                animate={{ scale: [1, 1.2, 1], opacity: [0.8, 0.15, 0.8] }}
                                transition={{ duration: 2.6, repeat: Infinity, ease: 'easeInOut' }}
                            />
                            <div className="text-center">
                                <p className="text-xs font-semibold text-white">Core App</p>
                                <p className="text-[10px] text-indigo-200 mt-0.5">12 domains</p>
                            </div>
                        </motion.div>

                        <div className="absolute left-4 right-4 bottom-4 grid grid-cols-2 gap-2 md:grid-cols-4">
                            {GRAPH_STATS.map((stat, index) => (
                                <motion.div
                                    key={stat.label}
                                    className="rounded-lg border border-white/10 bg-zinc-900/75 px-3 py-2"
                                    initial={{ opacity: 0, y: 8 }}
                                    whileInView={{ opacity: 1, y: 0 }}
                                    transition={{ duration: 0.35, delay: 0.38 + index * 0.07 }}
                                    viewport={{ once: true }}
                                >
                                    <p className="text-sm font-semibold text-white">{stat.value}</p>
                                    <p className="text-[10px] uppercase tracking-wider text-zinc-400 mt-0.5">{stat.label}</p>
                                </motion.div>
                            ))}
                        </div>
                    </div>
                </BentoCard>

                {/* 2. Learning Card (Top Right) */}
                <BentoCard
                    className="md:col-span-2 relative flex flex-col md:overflow-y-auto md:overscroll-y-contain"
                    delay={0.2}
                    onWheelCapture={handleScrollableCardWheel}
                >
                    <div className="flex items-center justify-between mb-4">
                        <div className="w-10 h-10 rounded-xl bg-purple-500/10 flex items-center justify-center border border-purple-500/20">
                            <GraduationCap className="text-purple-400" size={20} />
                        </div>
                        <span className="text-xs font-medium px-2 py-1 rounded-full bg-white/5 border border-white/5 text-zinc-400">
                            {ROLE_PATHS.length} Roles
                        </span>
                    </div>

                    <h3 className="text-xl font-semibold text-white mb-2">Personalized Syllabi</h3>
                    <p className="text-sm text-zinc-300 mb-4 leading-relaxed">
                        AI-generated role tracks that adapt to your pace, architecture scope, and code ownership.
                    </p>

                    <div className="rounded-2xl border border-white/10 bg-zinc-950/50 p-3 mb-4">
                        <div className="text-xs text-zinc-400 mb-3">Current Module Progress</div>
                        <div className="space-y-3">
                            {MODULE_PROGRESS.map((module, i) => (
                                <div key={module.label}>
                                    <div className="mb-1 flex items-center justify-between text-xs">
                                        <span className="text-zinc-200">{module.label}</span>
                                        <span className="text-zinc-400">{module.progress}%</span>
                                    </div>
                                    <div className="h-1.5 rounded-full bg-zinc-800 overflow-hidden">
                                        <motion.div
                                            className={`h-full rounded-full bg-gradient-to-r ${module.tone}`}
                                            initial={{ width: 0 }}
                                            whileInView={{ width: `${module.progress}%` }}
                                            transition={{ duration: 0.7, delay: 0.25 + i * 0.1 }}
                                            viewport={{ once: true }}
                                        />
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    <div className="space-y-2 pr-1">
                        {ROLE_PATHS.map((item, i) => (
                            <div key={i} className="flex items-center justify-between gap-2 text-sm text-zinc-200 p-2 rounded-lg bg-white/5 hover:bg-white/10 transition-colors cursor-default">
                                <span className="flex items-center gap-2 min-w-0">
                                    <CheckCircle2 size={14} className="text-purple-400 shrink-0" />
                                    <span className="truncate">{item}</span>
                                </span>
                                <span className="text-[10px] uppercase tracking-wider text-zinc-500">Path</span>
                            </div>
                        ))}
                    </div>
                </BentoCard>

                {/* 3. Gamification Card (Bottom Right) */}
                <BentoCard className="md:col-span-2 relative overflow-hidden" delay={0.3}>
                    <div className="absolute top-0 right-0 w-32 h-32 bg-amber-500/10 rounded-full blur-[40px] pointer-events-none" />

                    <div className="w-10 h-10 rounded-xl bg-amber-500/10 flex items-center justify-center border border-amber-500/20 mb-4">
                        <Trophy className="text-amber-400" size={20} />
                    </div>

                    <h3 className="text-xl font-semibold text-white mb-2">Gamified Mastery</h3>
                    <p className="text-sm text-zinc-300 mb-5 leading-relaxed">
                        Earn XP, maintain streaks, and unlock achievements as you explore.
                    </p>

                    <div className="mb-4 grid grid-cols-2 gap-2 text-xs">
                        <div className="rounded-lg border border-white/10 bg-zinc-900/60 px-3 py-2">
                            <p className="text-zinc-400">Weekly Streak</p>
                            <p className="mt-1 flex items-center gap-1 text-amber-300 font-semibold">
                                <Flame size={13} className="text-amber-400" />
                                6 days
                            </p>
                        </div>
                        <div className="rounded-lg border border-white/10 bg-zinc-900/60 px-3 py-2">
                            <p className="text-zinc-400">Challenges</p>
                            <p className="mt-1 font-semibold text-emerald-300">14 cleared</p>
                        </div>
                    </div>

                    {/* XP Bar Mock */}
                    <div className="bg-zinc-950/50 rounded-lg p-3 border border-white/5 mb-3">
                        <div className="flex justify-between text-xs text-zinc-400 mb-1">
                            <span>Level 3</span>
                            <span className="text-amber-400">1,250 XP</span>
                        </div>
                        <div className="w-full h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                            <motion.div
                                className="h-full bg-gradient-to-r from-amber-500 to-orange-500"
                                initial={{ width: '0%' }}
                                whileInView={{ width: '70%' }}
                                transition={{ duration: 1, ease: 'easeOut' }}
                            />
                        </div>
                    </div>

                    <div className="flex flex-wrap gap-2">
                        {['Explorer', 'Bug Hunter', 'Data Mapper'].map((badge) => (
                            <span key={badge} className="rounded-full border border-amber-400/20 bg-amber-500/10 px-2.5 py-1 text-[11px] text-amber-200">
                                {badge}
                            </span>
                        ))}
                    </div>
                </BentoCard>
            </div>
        </section>
    );
}
