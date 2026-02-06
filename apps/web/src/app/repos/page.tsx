'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import { Code2 } from 'lucide-react';
import { RepoList } from '@/components/repos/repo-list';
import { api, Repository } from '@/lib/api-client';
import { useEffect, useState } from 'react';

export default function ReposPage() {
    const [repos, setRepos] = useState<Repository[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function fetchRepos() {
            try {
                const data = await api.listRepos();
                setRepos(data.repositories);
            } catch (error) {
                console.error('Failed to fetch repos:', error);
            } finally {
                setLoading(false);
            }
        }
        fetchRepos();
    }, []);

    return (
        <div className="min-h-screen bg-zinc-950">
            {/* Header */}
            <nav className="border-b border-white/5 fixed top-0 w-full bg-zinc-950/80 backdrop-blur-md z-50">
                <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
                    <Link href="/" className="flex items-center gap-2 group">
                        <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center group-hover:bg-indigo-500 transition-colors">
                            <Code2 className="text-white" size={18} />
                        </div>
                        <span className="font-semibold text-white">CodebaseQA</span>
                    </Link>

                    <div className="flex items-center gap-4">
                        <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/5 text-xs text-zinc-400">
                            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                            System Normal
                        </div>
                    </div>
                </div>
            </nav>

            {/* Content */}
            <main className="max-w-5xl mx-auto px-6 pt-32 pb-10">
                <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mb-12 text-center"
                >
                    <h1 className="text-4xl font-bold text-white mb-4 tracking-tight">Your Repositories</h1>
                    <p className="text-zinc-400 max-w-xl mx-auto text-lg">
                        Manage your indexed codebases. Select a repository to launch the <span className="text-zinc-200 font-medium">Chat</span>, view the <span className="text-zinc-200 font-medium">Graph</span>, or start a <span className="text-zinc-200 font-medium">Course</span>.
                    </p>
                </motion.div>

                {loading ? (
                    <div className="flex justify-center py-32">
                        <div className="w-8 h-8 border-2 border-indigo-500/30 border-t-indigo-500 rounded-full animate-spin" />
                    </div>
                ) : (
                    <RepoList initialRepos={repos} />
                )}
            </main>
        </div>
    );
}
