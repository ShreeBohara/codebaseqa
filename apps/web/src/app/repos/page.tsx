'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import { RepoList } from '@/components/repos/repo-list';
import { PlatformConfig, api, Repository } from '@/lib/api-client';
import { useEffect, useState } from 'react';
import { DemoBanner } from '@/components/common/demo-banner';
import { BrandLogo } from '@/components/common/brand-logo';
import { SiteFooter } from '@/components/common/site-footer';

export default function ReposPage() {
    const [repos, setRepos] = useState<Repository[]>([]);
    const [platformConfig, setPlatformConfig] = useState<PlatformConfig | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function fetchRepos() {
            try {
                const [data, config] = await Promise.all([
                    api.listRepos(),
                    api.getPlatformConfig().catch(() => null),
                ]);
                setRepos(data.repositories);
                setPlatformConfig(config);
            } catch (error) {
                console.error('Failed to fetch repos:', error);
            } finally {
                setLoading(false);
            }
        }
        fetchRepos();
    }, []);

    return (
        <div className="bg-zinc-950">
            <div className="min-h-screen">
                {/* Header */}
                <nav className="border-b border-white/5 fixed top-0 w-full bg-zinc-950/80 backdrop-blur-md z-50">
                    <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
                        <Link href="/" className="flex items-center gap-2 group">
                            <BrandLogo labelClassName="group-hover:text-cyan-200" />
                        </Link>

                    </div>
                </nav>

                <DemoBanner platformConfig={platformConfig} className="mt-[73px]" />

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
                        <RepoList initialRepos={repos} platformConfig={platformConfig} />
                    )}
                </main>
            </div>
            <SiteFooter />
        </div>
    );
}
