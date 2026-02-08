'use client';

import { motion } from 'framer-motion';
import { Network, GraduationCap, Trophy, CheckCircle2 } from 'lucide-react';
import { ReactNode } from 'react';

// Card Component
function BentoCard({ children, className, delay = 0 }: { children: ReactNode; className?: string; delay?: number }) {
    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5, delay }}
            className={`bg-zinc-900/40 border border-white/5 p-6 rounded-3xl backdrop-blur-sm overflow-hidden relative group hover:border-white/10 transition-colors ${className}`}
        >
            {children}
        </motion.div>
    );
}

export function BentoGrid() {
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

            <div className="grid grid-cols-1 md:grid-cols-6 md:grid-rows-2 gap-4 h-auto md:h-[600px]">
                {/* 1. Visualizer Card (Large Left) */}
                <BentoCard className="md:col-span-4 md:row-span-2 relative flex flex-col justify-between overflow-hidden">
                    <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-indigo-500/10 rounded-full blur-[80px] -translate-y-1/2 translate-x-1/2 pointer-events-none" />

                    <div className="relative z-10">
                        <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 flex items-center justify-center mb-4 border border-indigo-500/20">
                            <Network className="text-indigo-400" />
                        </div>
                        <h3 className="text-2xl font-semibold text-white mb-2">Interactive Dependency Graph</h3>
                        <p className="text-zinc-400 max-w-sm">
                            Don&apos;t just read code, see it. Automatically generate and explore component relationships, API calls, and database schema connections.
                        </p>
                    </div>

                    {/* Mock Graph Visual */}
                    <div className="mt-8 flex-1 w-full bg-zinc-950/50 rounded-xl border border-white/5 p-4 relative overflow-hidden group-hover:border-indigo-500/20 transition-colors">
                        {/* Fake Nodes */}
                        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-full">
                            {/* Central Node */}
                            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-16 h-16 bg-indigo-600 rounded-full flex items-center justify-center shadow-lg shadow-indigo-500/20 border-4 border-zinc-900 z-20">
                                <span className="text-xs font-bold text-white">App</span>
                            </div>
                            {/* Orbiting Nodes */}
                            {[0, 60, 120, 180, 240, 300].map((deg, i) => (
                                <motion.div
                                    key={i}
                                    className="absolute top-1/2 left-1/2 w-3 h-3 bg-zinc-700 rounded-full"
                                    initial={{ x: 0, y: 0, opacity: 0 }}
                                    animate={{
                                        x: Math.cos(deg * Math.PI / 180) * 100,
                                        y: Math.sin(deg * Math.PI / 180) * 80,
                                        opacity: 1
                                    }}
                                    transition={{ duration: 1, delay: 0.2 + i * 0.1 }}
                                >
                                    {/* Connecting Line */}
                                    <div className="absolute top-1/2 left-1/2 w-[100px] h-[1px] bg-white/10 origin-left -z-10"
                                        style={{ transform: `rotate(${deg + 180}deg)`, width: '100px', left: '50%', top: '50%' }}
                                    />
                                </motion.div>
                            ))}
                        </div>
                    </div>
                </BentoCard>

                {/* 2. Learning Card (Top Right) */}
                <BentoCard className="md:col-span-2 relative" delay={0.2}>
                    <div className="flex items-center justify-between mb-4">
                        <div className="w-10 h-10 rounded-xl bg-purple-500/10 flex items-center justify-center border border-purple-500/20">
                            <GraduationCap className="text-purple-400" size={20} />
                        </div>
                        <span className="text-xs font-medium px-2 py-1 rounded-full bg-white/5 border border-white/5 text-zinc-400">
                            4 Modules
                        </span>
                    </div>
                    <h3 className="text-xl font-semibold text-white mb-2">Personalized Syllabi</h3>
                    <p className="text-sm text-zinc-400 mb-4">
                        AI-generated courses tailored to your role. From &quot;New Hire&quot; to &quot;Senior Architect&quot;.
                    </p>
                    <div className="space-y-2">
                        {['Architecture', 'Auth Flow', 'Database'].map((item, i) => (
                            <div key={i} className="flex items-center gap-2 text-sm text-zinc-300 p-2 rounded-lg bg-white/5 hover:bg-white/10 transition-colors cursor-default">
                                <CheckCircle2 size={14} className="text-purple-400" />
                                {item}
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
                    <p className="text-sm text-zinc-400 mb-6">
                        Earn XP, maintain streaks, and unlock achievements as you explore.
                    </p>

                    {/* XP Bar Mock */}
                    <div className="bg-zinc-950/50 rounded-lg p-3 border border-white/5">
                        <div className="flex justify-between text-xs text-zinc-400 mb-1">
                            <span>Level 3</span>
                            <span className="text-amber-400">1,250 XP</span>
                        </div>
                        <div className="w-full h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                            <motion.div
                                className="h-full bg-gradient-to-r from-amber-500 to-orange-500"
                                initial={{ width: "0%" }}
                                whileInView={{ width: "70%" }}
                                transition={{ duration: 1, ease: "easeOut" }}
                            />
                        </div>
                    </div>
                </BentoCard>
            </div>
        </section>
    );
}
