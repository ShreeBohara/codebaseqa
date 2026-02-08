import Link from 'next/link';
import { redirect } from 'next/navigation';
import { Code2, ArrowLeft } from 'lucide-react';
import { api } from '@/lib/api-client';
import { ChatInterface } from '@/components/chat/chat-interface';
import { DemoBanner } from '@/components/common/demo-banner';

export const dynamic = 'force-dynamic';

interface ChatPageProps {
    params: Promise<{ repoId: string }>;
}

export default async function ChatPage({ params }: ChatPageProps) {
    const { repoId } = await params;

    let repo;
    let session;

    try {
        repo = await api.getRepo(repoId);

        if (repo.status !== 'completed') {
            redirect(`/repos`);
        }

        session = await api.createSession(repoId);
    } catch {
        redirect('/repos');
    }

    return (
        <div className="h-screen flex flex-col bg-zinc-950">
            {/* Header */}
            <header className="flex-shrink-0 bg-zinc-900/50 border-b border-zinc-800">
                <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
                    <Link href="/repos" className="flex items-center gap-2 text-zinc-400 hover:text-white transition-colors">
                        <ArrowLeft size={18} />
                        <span className="text-sm">Repositories</span>
                    </Link>

                    <div className="flex items-center gap-2">
                        <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center">
                            <Code2 className="text-white" size={14} />
                        </div>
                        <span className="font-semibold text-white">CodebaseQA</span>
                    </div>

                    <div className="text-sm text-zinc-400">
                        {repo.github_owner}/{repo.github_name}
                    </div>
                </div>
            </header>

            <DemoBanner />

            {/* Chat Interface */}
            <div className="flex-1 overflow-hidden">
                <ChatInterface
                    sessionId={session.id}
                    repoName={`${repo.github_owner}/${repo.github_name}`}
                />
            </div>
        </div>
    );
}
