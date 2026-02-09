import { GitBranch } from 'lucide-react';
import { cn } from '@/lib/utils';

interface RepoContextBadgeProps {
    repoName: string;
    className?: string;
    compact?: boolean;
}

export function RepoContextBadge({ repoName, className, compact = false }: RepoContextBadgeProps) {
    return (
        <div
            className={cn(
                'inline-flex min-w-0 items-center gap-2 rounded-lg border border-zinc-700/80 bg-zinc-900/80 px-2.5 py-1.5 text-zinc-200',
                className
            )}
        >
            <GitBranch size={compact ? 13 : 14} className="shrink-0 text-emerald-300" />
            <div className="min-w-0">
                {!compact && (
                    <p className="text-[10px] uppercase tracking-[0.12em] text-zinc-500">
                        Repository
                    </p>
                )}
                <p className={cn('truncate font-medium text-zinc-100', compact ? 'text-xs' : 'text-[13px]')} title={repoName}>
                    {repoName}
                </p>
            </div>
        </div>
    );
}
