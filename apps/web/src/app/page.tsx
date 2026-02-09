'use client';

import Link from 'next/link';
import { Github, Globe } from 'lucide-react';
import { HeroSection } from '@/components/home/hero-section';
import { BentoGrid } from '@/components/home/bento-grid';
import { DemoBanner } from '@/components/common/demo-banner';
import { BrandLogo } from '@/components/common/brand-logo';
import { SiteFooter } from '@/components/common/site-footer';

const PORTFOLIO_URL = 'https://shreebohara.com/';

export default function Home() {
  return (
    <div className="bg-zinc-950">
      <div className="min-h-screen">
        {/* Nav */}
        <nav className="border-b border-white/5 fixed top-0 w-full bg-zinc-950/80 backdrop-blur-md z-50">
          <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
            <BrandLogo />
            <div className="flex items-center gap-6">
              <Link
                href={PORTFOLIO_URL}
                className="text-zinc-400 hover:text-white transition-colors hidden sm:inline-flex"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="Portfolio website"
              >
                <Globe size={18} />
              </Link>
              <Link
                href="https://github.com/ShreeBohara/codebaseqa"
                className="text-zinc-400 hover:text-white transition-colors hidden sm:inline-flex"
                target="_blank"
                rel="noopener noreferrer"
                aria-label="GitHub repository"
              >
                <Github size={18} />
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
      </div>
      <SiteFooter className="mt-12" />
    </div>
  );
}
