'use client';

import { motion } from 'framer-motion';
import Link from 'next/link';
import { ArrowRight, Github, Sparkles, Network } from 'lucide-react';
import { useState, useEffect } from 'react';

const ROLES = [
    { text: "New Hires", color: "text-emerald-400" },
    { text: "Architects", color: "text-purple-400" },
    { text: "Auditors", color: "text-rose-400" },
    { text: "Developers", color: "text-indigo-400" },
];

export function HeroSection() {
    const [roleIndex, setRoleIndex] = useState(0);

    useEffect(() => {
        const interval = setInterval(() => {
            setRoleIndex((prev) => (prev + 1) % ROLES.length);
        }, 3000);
        return () => clearInterval(interval);
    }, []);

    return (
        <section className="relative px-6 pt-32 pb-24 md:pt-48 md:pb-32 overflow-hidden">
            {/* Background Effects */}
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full h-full max-w-7xl -z-10 pointer-events-none">
                <div className="absolute top-[20%] left-[10%] w-[500px] h-[500px] bg-indigo-500/20 rounded-full blur-[120px] mix-blend-screen animate-pulse" />
                <div className="absolute top-[30%] right-[10%] w-[400px] h-[400px] bg-purple-500/20 rounded-full blur-[100px] mix-blend-screen" />
            </div>

            <div className="max-w-5xl mx-auto text-center z-10">
                <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.5 }}
                >
                    {/* Badge */}
                    <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-sm text-zinc-300 mb-8 backdrop-blur-md shadow-lg shadow-black/20">
                        <Sparkles size={14} className="text-amber-400" />
                        <span className="font-medium bg-gradient-to-r from-amber-200 to-yellow-400 bg-clip-text text-transparent">
                            V2.0: Now with Autopilot
                        </span>
                    </div>

                    <h1 className="text-5xl md:text-7xl font-bold text-white tracking-tight mb-8 leading-tight">
                        Master any codebase <br className="hidden md:block" />
                        for <span className={`transition-colors duration-500 ${ROLES[roleIndex].color}`}>
                            {ROLES[roleIndex].text}
                        </span>
                    </h1>

                    <p className="text-zinc-400 text-lg md:text-xl mb-10 max-w-2xl mx-auto leading-relaxed">
                        Stop searching blindly. Generate <span className="text-white font-medium">dependency graphs</span>,
                        personalized <span className="text-white font-medium">learning paths</span>, and
                        interactive <span className="text-white font-medium">challenges</span> instantly.
                    </p>

                    <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                        <Link
                            href="/repos"
                            className="group w-full sm:w-auto inline-flex items-center justify-center gap-2 bg-white text-black hover:bg-zinc-200 px-8 py-4 rounded-2xl font-semibold transition-all shadow-xl shadow-white/5 md:text-lg"
                        >
                            Start Learning
                            <ArrowRight size={18} className="group-hover:translate-x-0.5 transition-transform" />
                        </Link>
                        <a
                            href="https://github.com/ShreeBohara/codebaseqa"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 bg-zinc-900 border border-zinc-800 hover:bg-zinc-800 text-white px-8 py-4 rounded-2xl font-medium transition-all md:text-lg"
                        >
                            <Github size={20} />
                            View on GitHub
                        </a>
                    </div>

                    {/* Trust Badges */}
                    <div className="mt-16 pt-8 border-t border-white/5 grid grid-cols-3 gap-4 max-w-2xl mx-auto">
                        <div className="text-center">
                            <div className="flex items-center justify-center gap-2 text-indigo-400 mb-1">
                                <Github size={20} />
                                <span className="font-bold text-xl">100%</span>
                            </div>
                            <div className="text-sm text-zinc-500">Open Source</div>
                        </div>
                        <div className="text-center border-l border-white/5 border-r">
                            <div className="flex items-center justify-center gap-2 text-purple-400 mb-1">
                                <Network size={20} />
                                <span className="font-bold text-xl">Local</span>
                            </div>
                            <div className="text-sm text-zinc-500">Self-Hosted</div>
                        </div>
                        <div className="text-center">
                            <div className="flex items-center justify-center gap-2 text-emerald-400 mb-1">
                                <Sparkles size={20} />
                                <span className="font-bold text-xl">BYOK</span>
                            </div>
                            <div className="text-sm text-zinc-500">Your API Keys</div>
                        </div>
                    </div>
                </motion.div>
            </div>
        </section>
    );
}
