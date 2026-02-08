'use client';

import { useState, FormEvent, useEffect } from 'react';
import Link from 'next/link';
import { motion, AnimatePresence } from 'framer-motion';
import { api, Repository } from '@/lib/api-client';
import {
    Github, Loader2, Trash2, ExternalLink,
    AlertCircle, Sparkles,
    MessageSquare, GraduationCap, Network, ArrowRight
} from 'lucide-react';

interface RepoCardProps {
    repo: Repository;
    onDelete: (id: string) => void;
}

function RepoCard({ repo, onDelete }: RepoCardProps) {
    const [isDeleting, setIsDeleting] = useState(false);

    const handleDelete = async (e: React.MouseEvent) => {
        e.stopPropagation();
        if (!confirm('Delete this repository?')) return;
        setIsDeleting(true);
        try {
            await api.deleteRepo(repo.id);
            onDelete(repo.id);
        } catch (error) {
            console.error('Failed to delete:', error);
        } finally {
            setIsDeleting(false);
        }
    };

    const statusConfig: Record<string, { color: string; bg: string; label: string; pulse?: boolean }> = {
        completed: { color: 'text-emerald-400', bg: 'bg-emerald-500/20', label: 'Ready' },
        failed: { color: 'text-red-400', bg: 'bg-red-500/20', label: 'Failed' },
        pending: { color: 'text-amber-400', bg: 'bg-amber-500/20', label: 'Queue', pulse: true },
        cloning: { color: 'text-blue-400', bg: 'bg-blue-500/20', label: 'Cloning', pulse: true },
        parsing: { color: 'text-indigo-400', bg: 'bg-indigo-500/20', label: 'Parsing', pulse: true },
        embedding: { color: 'text-purple-400', bg: 'bg-purple-500/20', label: 'Embedding', pulse: true },
    };

    const status = statusConfig[repo.status] || statusConfig.pending;
    const isReady = repo.status === 'completed';
    const statusHelpText: Partial<Record<Repository['status'], string>> = {
        embedding: 'Embedding can hit provider rate limits (HTTP 429). Retries are automatic and indexing will continue.',
    };
    const helpText = statusHelpText[repo.status];

    return (
        <motion.div
            layout
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            whileHover={{ y: -5 }}
            className={`group relative bg-zinc-900/40 border border-white/5 rounded-3xl p-6 backdrop-blur-sm overflow-hidden transition-colors ${isReady ? 'hover:border-indigo-500/30' : 'opacity-80'
                }`}
        >
            {/* Status Indicator */}
            <div className="absolute top-6 right-6 flex items-center gap-2">
                {status.pulse && (
                    <span className="relative flex h-2 w-2">
                        <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${status.color.replace('text-', 'bg-')}`}></span>
                        <span className={`relative inline-flex rounded-full h-2 w-2 ${status.color.replace('text-', 'bg-')}`}></span>
                    </span>
                )}
                <span className={`text-xs font-medium ${status.color}`}>{status.label}</span>
            </div>

            {/* Icon & Title */}
            <div className="flex items-center gap-4 mb-6">
                <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-zinc-800 to-zinc-900 border border-white/5 flex items-center justify-center shadow-lg group-hover:shadow-indigo-500/10 transition-shadow">
                    <Github size={22} className="text-zinc-300" />
                </div>
                <div className="flex-1 min-w-0 pr-8">
                    <h3 className="font-semibold text-white text-lg truncate" title={`${repo.github_owner}/${repo.github_name}`}>
                        {repo.github_name}
                    </h3>
                    <p className="text-sm text-zinc-500 truncate">{repo.github_owner}</p>
                </div>
            </div>

            {/* Actions Grid */}
            <div className="grid grid-cols-3 gap-2 mb-6">
                <Link
                    href={isReady ? `/repos/${repo.id}/chat` : '#'}
                    className={`flex flex-col items-center justify-center gap-1.5 p-3 rounded-xl border border-white/5 transition-colors ${isReady
                        ? 'bg-zinc-800/20 hover:bg-indigo-500/10 hover:border-indigo-500/20 text-indigo-300'
                        : 'bg-zinc-800/10 text-zinc-600 cursor-not-allowed'
                        }`}
                >
                    <MessageSquare size={18} />
                    <span className="text-xs font-medium">Chat</span>
                </Link>
                <Link
                    href={isReady ? `/repos/${repo.id}/learn` : '#'}
                    className={`flex flex-col items-center justify-center gap-1.5 p-3 rounded-xl border border-white/5 transition-colors ${isReady
                        ? 'bg-zinc-800/20 hover:bg-purple-500/10 hover:border-purple-500/20 text-purple-300'
                        : 'bg-zinc-800/10 text-zinc-600 cursor-not-allowed'
                        }`}
                >
                    <GraduationCap size={18} />
                    <span className="text-xs font-medium">Learn</span>
                </Link>
                <Link
                    href={isReady ? `/repos/${repo.id}/learn?tab=graph` : '#'}
                    onClick={(e) => e.stopPropagation()}
                    className={`flex flex-col items-center justify-center gap-1.5 p-3 rounded-xl border border-white/5 transition-colors ${isReady
                        ? 'bg-zinc-800/20 hover:bg-emerald-500/10 hover:border-emerald-500/20 text-emerald-300 cursor-pointer'
                        : 'bg-zinc-800/10 text-zinc-600 cursor-not-allowed'
                        }`}
                >
                    <Network size={18} />
                    <span className="text-xs font-medium">Graph</span>
                </Link>
            </div>

            {helpText && (
                <div className="mb-4 rounded-xl border border-amber-500/20 bg-amber-500/5 px-3 py-2 text-xs text-amber-200/90 flex items-start gap-2">
                    <AlertCircle size={14} className="mt-0.5 shrink-0 text-amber-300" />
                    <span>{helpText}</span>
                </div>
            )}

            {/* Footer */}
            <div className="flex items-center justify-between text-xs text-zinc-500 pt-4 border-t border-white/5">
                <div className="flex items-center gap-3">
                    {repo.primary_language && (
                        <div className="flex items-center gap-1.5">
                            <span className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
                            {repo.primary_language}
                        </div>
                    )}
                    <span>{repo.total_files || 0} files</span>
                </div>

                <div className="flex items-center gap-1">
                    <a
                        href={repo.github_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="p-1.5 hover:text-white rounded-lg hover:bg-white/5"
                    >
                        <ExternalLink size={14} />
                    </a>
                    <button
                        onClick={handleDelete}
                        disabled={isDeleting}
                        className="p-1.5 hover:text-red-400 rounded-lg hover:bg-red-500/10"
                    >
                        {isDeleting ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
                    </button>
                </div>
            </div>
        </motion.div>
    );
}

interface AddRepoFormProps {
    onAdd: (repo: Repository) => void;
    prefillUrl?: string;
    onPrefillUsed?: () => void;
}

export function AddRepoForm({ onAdd, prefillUrl, onPrefillUsed }: AddRepoFormProps) {
    const [url, setUrl] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState('');

    // Handle prefill from parent
    useEffect(() => {
        if (prefillUrl) {
            setUrl(prefillUrl);
            onPrefillUsed?.();
        }
    }, [prefillUrl, onPrefillUsed]);

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        if (!url.trim()) return;
        setIsLoading(true);
        setError('');
        try {
            const repo = await api.createRepo(url.trim());
            onAdd(repo);
            setUrl('');
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to add repository');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <form onSubmit={handleSubmit} className="relative w-full max-w-2xl mx-auto mb-16">
            <div className="relative group">
                <div className="absolute -inset-0.5 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-2xl opacity-20 group-hover:opacity-40 transition duration-500 blur"></div>
                <div className="relative flex items-center bg-zinc-900 border border-white/10 rounded-2xl p-2 shadow-2xl">
                    <div className="pl-4 pr-3 text-zinc-500">
                        <Github size={20} />
                    </div>
                    <input
                        type="text"
                        value={url}
                        onChange={(e) => setUrl(e.target.value)}
                        placeholder="paste your github repository url..."
                        className="flex-1 bg-transparent border-none text-white placeholder:text-zinc-600 focus:outline-none focus:ring-0 text-sm py-3"
                        disabled={isLoading}
                    />
                    <button
                        type="submit"
                        disabled={isLoading || !url.trim()}
                        className="bg-white text-black hover:bg-zinc-200 disabled:opacity-50 disabled:cursor-not-allowed px-6 py-3 rounded-xl text-sm font-semibold transition-all flex items-center gap-2"
                    >
                        {isLoading ? <Loader2 size={16} className="animate-spin" /> : (
                            <>
                                <span>Import</span>
                                <ArrowRight size={16} />
                            </>
                        )}
                    </button>
                </div>
            </div>
            {error && (
                <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="absolute -bottom-8 left-0 text-red-400 text-xs flex items-center gap-1.5"
                >
                    <AlertCircle size={12} />
                    {error}
                </motion.div>
            )}
        </form>
    );
}

interface RepoListProps {
    initialRepos: Repository[];
}

export function RepoList({ initialRepos }: RepoListProps) {
    const [repos, setRepos] = useState<Repository[]>(initialRepos);
    const [prefillUrl, setPrefillUrl] = useState<string>('');
    const [loadingDemo, setLoadingDemo] = useState(false);

    const handleLoadDemo = async () => {
        setLoadingDemo(true);
        try {
            const result = await api.seedDemo();
            if (result.status === 'ready' || result.status === 'indexing') {
                // Refresh the repos list
                const data = await api.listRepos();
                setRepos(data.repositories);
            }
        } catch (error) {
            console.error('Failed to load demo:', error);
            alert('Failed to load demo repository. Make sure the API is running.');
        } finally {
            setLoadingDemo(false);
        }
    };

    // Poll for updates if any repo is in a pending/processing state
    useEffect(() => {
        const hasPending = repos.some(r => ['pending', 'cloning', 'parsing', 'embedding'].includes(r.status));
        if (!hasPending) return;

        const interval = setInterval(async () => {
            const data = await api.listRepos();
            setRepos(data.repositories);
        }, 3000);

        return () => clearInterval(interval);
    }, [repos]);

    return (
        <div>
            <div className="pt-8">
                <AddRepoForm
                    onAdd={(repo) => setRepos((prev) => [repo, ...prev])}
                    prefillUrl={prefillUrl}
                    onPrefillUsed={() => setPrefillUrl('')}
                />
            </div>

            <AnimatePresence mode="popLayout">
                {repos.length === 0 ? (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="py-12"
                    >
                        {/* Empty State Hero */}
                        <div className="text-center mb-12">
                            <div className="relative w-24 h-24 mx-auto mb-6">
                                <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/20 to-purple-500/20 rounded-full blur-xl" />
                                <div className="relative w-24 h-24 bg-zinc-900/80 rounded-full flex items-center justify-center border border-white/10">
                                    <Sparkles size={36} className="text-indigo-400" />
                                </div>
                            </div>
                            <h3 className="text-2xl font-bold text-white mb-3">Start Your Journey</h3>
                            <p className="text-zinc-400 max-w-md mx-auto mb-6">
                                Import any public GitHub repository to explore its architecture,
                                chat with the code, and generate personalized learning paths.
                            </p>

                            {/* Quick Demo Button */}
                            <button
                                onClick={handleLoadDemo}
                                disabled={loadingDemo}
                                className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white rounded-xl font-medium transition-all shadow-lg shadow-indigo-500/25 disabled:opacity-50"
                            >
                                {loadingDemo ? (
                                    <>
                                        <Loader2 size={18} className="animate-spin" />
                                        Loading Demo...
                                    </>
                                ) : (
                                    <>
                                        <Sparkles size={18} />
                                        Load Demo Repository
                                    </>
                                )}
                            </button>
                            <p className="text-xs text-zinc-500 mt-2">
                                Try with a pre-configured example project
                            </p>
                        </div>

                        {/* Example Repos */}
                        <div className="max-w-2xl mx-auto">
                            <p className="text-xs uppercase tracking-wider text-zinc-500 font-medium mb-4 text-center">
                                Try these popular repositories
                            </p>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                {[
                                    { name: 'expressjs/express', desc: 'Fast, minimal web framework' },
                                    { name: 'facebook/react', desc: 'UI component library' },
                                    { name: 'fastapi/fastapi', desc: 'Modern Python web framework' },
                                    { name: 'vercel/next.js', desc: 'React framework for production' },
                                ].map((example) => (
                                    <button
                                        key={example.name}
                                        onClick={() => setPrefillUrl(`https://github.com/${example.name}`)}
                                        className="group flex items-center gap-3 p-4 bg-zinc-900/50 border border-white/5 rounded-xl hover:border-indigo-500/30 hover:bg-zinc-900/80 transition-all text-left"
                                    >
                                        <div className="w-10 h-10 rounded-lg bg-zinc-800 flex items-center justify-center group-hover:bg-indigo-500/20 transition-colors">
                                            <Github size={18} className="text-zinc-400 group-hover:text-indigo-400 transition-colors" />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-medium text-white truncate">{example.name}</p>
                                            <p className="text-xs text-zinc-500 truncate">{example.desc}</p>
                                        </div>
                                        <ArrowRight size={14} className="text-zinc-600 group-hover:text-indigo-400 transition-colors" />
                                    </button>
                                ))}
                            </div>
                        </div>
                    </motion.div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-2 gap-6 pb-24">
                        {repos.map((repo) => (
                            <RepoCard key={repo.id} repo={repo} onDelete={(id) => setRepos((prev) => prev.filter((r) => r.id !== id))} />
                        ))}
                    </div>
                )}
            </AnimatePresence>
        </div>
    );
}
