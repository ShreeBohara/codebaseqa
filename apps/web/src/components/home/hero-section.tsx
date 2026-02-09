'use client';

import { motion } from 'framer-motion';
import Link from 'next/link';
import { ArrowRight, Github, Globe, Sparkles, Network } from 'lucide-react';
import { useState, useEffect } from 'react';

const ROLES = [
    { text: "New Hires", color: "text-emerald-400" },
    { text: "Architects", color: "text-purple-400" },
    { text: "Auditors", color: "text-rose-400" },
    { text: "Developers", color: "text-indigo-400" },
];
const LONGEST_ROLE_LENGTH = Math.max(...ROLES.map((role) => role.text.length));

const TYPE_SPEED_MS = 85;
const DELETE_SPEED_MS = 55;
const HOLD_TYPED_MS = 1200;
const HOLD_EMPTY_MS = 200;
const PORTFOLIO_URL = 'https://shreebohara.com/';

export function HeroSection() {
    const [roleIndex, setRoleIndex] = useState(0);
    const [typedText, setTypedText] = useState('');
    const [isDeleting, setIsDeleting] = useState(false);

    useEffect(() => {
        const currentRole = ROLES[roleIndex].text;

        if (!isDeleting && typedText.length < currentRole.length) {
            const timeout = setTimeout(() => {
                setTypedText(currentRole.slice(0, typedText.length + 1));
            }, TYPE_SPEED_MS);
            return () => clearTimeout(timeout);
        }

        if (!isDeleting && typedText.length === currentRole.length) {
            const timeout = setTimeout(() => {
                setIsDeleting(true);
            }, HOLD_TYPED_MS);
            return () => clearTimeout(timeout);
        }

        if (isDeleting && typedText.length > 0) {
            const timeout = setTimeout(() => {
                setTypedText(currentRole.slice(0, typedText.length - 1));
            }, DELETE_SPEED_MS);
            return () => clearTimeout(timeout);
        }

        const timeout = setTimeout(() => {
            setIsDeleting(false);
            setRoleIndex((prev) => (prev + 1) % ROLES.length);
        }, HOLD_EMPTY_MS);
        return () => clearTimeout(timeout);
    }, [isDeleting, roleIndex, typedText]);

    return (
        <section className="relative min-h-[100svh] px-6 pt-36 pb-20 md:pt-56 md:pb-24 overflow-hidden">
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
                    <h1 className="text-5xl md:text-7xl font-bold text-white tracking-tight mb-8 leading-tight">
                        Master any codebase <br className="hidden md:block" />
                        for <span
                            className={`inline-block whitespace-nowrap text-left transition-colors duration-300 ${ROLES[roleIndex].color}`}
                            style={{ minWidth: `${LONGEST_ROLE_LENGTH + 1}ch` }}
                        >
                            {typedText}
                            <span className="animate-pulse">|</span>
                        </span>
                    </h1>

                    <p className="text-zinc-400 text-lg md:text-xl mb-10 max-w-2xl mx-auto leading-relaxed">
                        Stop searching blindly. <span className="text-white font-medium">Chat with your codebase</span> to get
                        instant answers, then generate <span className="text-white font-medium">dependency graphs</span>,
                        personalized <span className="text-white font-medium">learning paths</span>, and
                        interactive <span className="text-white font-medium">challenges</span>.
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
                        <a
                            href={PORTFOLIO_URL}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 bg-zinc-900 border border-zinc-800 hover:bg-zinc-800 text-white px-8 py-4 rounded-2xl font-medium transition-all md:text-lg"
                        >
                            <Globe size={20} />
                            Portfolio
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
