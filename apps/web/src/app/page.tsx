'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import { Code2, ArrowRight, Github, Sparkles, Search, BookOpen, MessageSquare } from 'lucide-react';

export default function Home() {
  return (
    <div className="min-h-screen bg-zinc-950">
      {/* Nav */}
      <nav className="border-b border-zinc-900">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center">
              <Code2 className="text-white" size={18} />
            </div>
            <span className="font-semibold text-white">CodebaseQA</span>
          </div>
          <Link
            href="/repos"
            className="text-sm text-zinc-400 hover:text-indigo-400 transition-colors"
          >
            Get Started →
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-3xl mx-auto px-6 pt-24 pb-16 text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="inline-flex items-center gap-2 text-sm text-indigo-400 mb-6">
            <Sparkles size={14} />
            AI-Powered Code Understanding
          </div>

          <h1 className="text-4xl md:text-5xl font-bold text-white leading-tight mb-4">
            Understand any codebase
            <br />
            <span className="text-zinc-500">in minutes</span>
          </h1>

          <p className="text-zinc-400 text-lg mb-8 max-w-xl mx-auto">
            Ask questions about any GitHub repository and get instant, accurate answers with source references.
          </p>

          <div className="flex items-center justify-center gap-4">
            <Link
              href="/repos"
              className="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-2.5 rounded-lg font-medium transition-colors"
            >
              Start Exploring
              <ArrowRight size={16} />
            </Link>
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-zinc-400 hover:text-white transition-colors"
            >
              <Github size={18} />
              View on GitHub
            </a>
          </div>
        </motion.div>
      </section>

      {/* Features */}
      <section className="max-w-4xl mx-auto px-6 py-16">
        <div className="grid md:grid-cols-3 gap-6">
          {[
            {
              icon: <MessageSquare size={20} />,
              title: "Natural Language Q&A",
              desc: "Ask questions in plain English about any codebase",
              color: "bg-indigo-500/10 text-indigo-400"
            },
            {
              icon: <Search size={20} />,
              title: "Semantic Search",
              desc: "Find code using natural language, not just keywords",
              color: "bg-emerald-500/10 text-emerald-400"
            },
            {
              icon: <BookOpen size={20} />,
              title: "Source References",
              desc: "Every answer includes links to the actual source code",
              color: "bg-amber-500/10 text-amber-400"
            }
          ].map((feature, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 + i * 0.1 }}
              className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-5 hover:border-zinc-700 transition-colors"
            >
              <div className={`w-10 h-10 rounded-lg ${feature.color} flex items-center justify-center mb-3`}>
                {feature.icon}
              </div>
              <h3 className="font-medium text-white mb-1">{feature.title}</h3>
              <p className="text-sm text-zinc-500">{feature.desc}</p>
            </motion.div>
          ))}
        </div>
      </section>

      {/* Demo */}
      <section className="max-w-3xl mx-auto px-6 pb-24">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden"
        >
          {/* Terminal header */}
          <div className="flex items-center gap-2 px-4 py-3 border-b border-zinc-800">
            <div className="flex gap-1.5">
              <div className="w-3 h-3 rounded-full bg-red-500/60" />
              <div className="w-3 h-3 rounded-full bg-yellow-500/60" />
              <div className="w-3 h-3 rounded-full bg-green-500/60" />
            </div>
            <span className="text-xs text-zinc-500 ml-2">codebase-qa</span>
          </div>

          {/* Demo content */}
          <div className="p-5 space-y-4">
            {/* User question */}
            <div className="flex justify-end">
              <div className="bg-indigo-600 text-white text-sm px-4 py-2 rounded-xl rounded-br-sm">
                What is the main entry point?
              </div>
            </div>

            {/* AI response */}
            <div className="text-sm text-zinc-300">
              <p className="mb-2">The main entry point is <code className="bg-indigo-500/15 text-indigo-300 px-1.5 py-0.5 rounded">src/app/layout.tsx</code></p>
              <div className="bg-zinc-950 border border-zinc-800 rounded-lg p-3 font-mono text-xs text-zinc-400">
                <span className="text-indigo-400">// src/app/layout.tsx</span>
                <br />
                export default function RootLayout() &#123;...&#125;
              </div>
            </div>
          </div>
        </motion.div>
      </section>

      {/* Footer */}
      <footer className="border-t border-zinc-900 py-6">
        <div className="max-w-5xl mx-auto px-6 text-center text-sm text-zinc-600">
          CodebaseQA • Self-hostable AI-powered codebase understanding
        </div>
      </footer>
    </div>
  );
}
