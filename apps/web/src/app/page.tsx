'use client';

import Link from 'next/link';
import { Code2 } from 'lucide-react';
import { HeroSection } from '@/components/home/hero-section';
import { BentoGrid } from '@/components/home/bento-grid';
import { DemoBanner } from '@/components/common/demo-banner';

export default function Home() {
  return (
    <div className="min-h-screen bg-zinc-950">
      {/* Nav */}
      <nav className="border-b border-white/5 fixed top-0 w-full bg-zinc-950/80 backdrop-blur-md z-50">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
              <Code2 className="text-white" size={18} />
            </div>
            <span className="font-semibold text-white">CodebaseQA</span>
          </div>
          <div className="flex items-center gap-6">
                        <Link
                            href="https://github.com/ShreeBohara/codebaseqa"
                            className="text-sm text-zinc-400 hover:text-white transition-colors hidden sm:block"
                            target="_blank"
                        >
                            GitHub
                        </Link>
            <Link
              href="/repos"
              className="text-sm px-4 py-2 bg-white text-black font-medium rounded-lg hover:bg-zinc-200 transition-colors"
            >
              Get Started
            </Link>
          </div>
        </div>
      </nav>
      <DemoBanner className="mt-[73px]" />

      {/* Hero */}
      <HeroSection />

      {/* Bento Grid Features */}
      <BentoGrid />

      {/* Footer */}
      <footer className="border-t border-white/5 py-12 mt-12 bg-zinc-950">
        <div className="max-w-6xl mx-auto px-6">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6 mb-8">
            <div className="flex items-center gap-2">
              <div className="w-6 h-6 rounded-md bg-zinc-800 flex items-center justify-center">
                <Code2 className="text-zinc-400" size={14} />
              </div>
              <span className="text-sm font-semibold text-zinc-400">CodebaseQA</span>
            </div>

            <div className="flex items-center gap-6">
              <Link
                href="https://github.com/ShreeBohara"
                target="_blank"
                className="text-sm text-zinc-500 hover:text-white transition-colors"
              >
                GitHub
              </Link>
              <Link
                href="https://linkedin.com/in/ShreeBohara"
                target="_blank"
                className="text-sm text-zinc-500 hover:text-white transition-colors"
              >
                LinkedIn
              </Link>
            </div>
          </div>

          <div className="pt-6 border-t border-white/5 flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="text-sm text-zinc-600">
              &copy; {new Date().getFullYear()} Open Source. MIT License.
            </div>
            <div className="text-sm text-zinc-500">
              Built by{' '}
              <Link
                href="https://github.com/ShreeBohara"
                target="_blank"
                className="text-indigo-400 hover:text-indigo-300 transition-colors font-medium"
              >
                Shree Bohara
              </Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
