'use client';

import Link from 'next/link';
import { Github, Globe, Linkedin } from 'lucide-react';
import { BrandLogo } from '@/components/common/brand-logo';
import { cn } from '@/lib/utils';

const PORTFOLIO_URL = 'https://shreebohara.com/';

interface SiteFooterProps {
    className?: string;
}

export function SiteFooter({ className }: SiteFooterProps) {
    return (
        <footer className={cn('border-t border-white/5 py-10 bg-zinc-950', className)}>
            <div className="max-w-6xl mx-auto px-6">
                <div className="rounded-2xl border border-white/5 bg-zinc-900/40 px-5 py-5 md:px-6 md:py-6">
                    <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
                        <div className="flex flex-col gap-2">
                            <BrandLogo size="sm" labelClassName="text-zinc-200" />
                            <p className="text-sm text-zinc-500">
                                &copy; {new Date().getFullYear()} Open Source. MIT License.
                            </p>
                        </div>

                        <div className="flex flex-wrap items-center gap-3 md:justify-end">
                            <Link
                                href="https://github.com/ShreeBohara"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-zinc-300 hover:bg-white/10 hover:text-white transition-colors"
                            >
                                <Github size={15} />
                                GitHub
                            </Link>
                            <Link
                                href={PORTFOLIO_URL}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-zinc-300 hover:bg-white/10 hover:text-white transition-colors"
                            >
                                <Globe size={15} />
                                Portfolio
                            </Link>
                            <Link
                                href="https://linkedin.com/in/ShreeBohara"
                                target="_blank"
                                rel="noopener noreferrer"
                                className="inline-flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-zinc-300 hover:bg-white/10 hover:text-white transition-colors"
                            >
                                <Linkedin size={15} />
                                LinkedIn
                            </Link>
                            <span className="text-sm text-zinc-500">
                                Built by{' '}
                                <Link
                                    href={PORTFOLIO_URL}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-indigo-400 hover:text-indigo-300 transition-colors font-medium"
                                >
                                    Shree Bohara
                                </Link>
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </footer>
    );
}
