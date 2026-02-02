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
      <section className="relative max-w-5xl mx-auto px-6 pt-32 pb-24 text-center z-10">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-indigo-500/10 rounded-full blur-[120px] -z-10" />

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-sm text-indigo-300 mb-8 backdrop-blur-md">
            <Sparkles size={14} />
            <span className="font-medium">AI-Powered Code Understanding 2.0</span>
          </div>

          <h1 className="text-5xl md:text-7xl font-bold text-white tracking-tight mb-6">
            Understand any codebase
            <br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-400 to-purple-400">in minutes</span>
          </h1>

          <p className="text-zinc-400 text-xl mb-10 max-w-2xl mx-auto leading-relaxed">
            Stop searching blindly. Ask questions, visualize data flow, and master new repositories instantly with clear source references.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link
              href="/repos"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 bg-white text-black hover:bg-zinc-200 px-8 py-3.5 rounded-xl font-semibold transition-all shadow-lg shadow-white/5"
            >
              Start Exploring
              <ArrowRight size={18} />
            </Link>
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 bg-zinc-900 border border-zinc-800 hover:bg-zinc-800 text-white px-8 py-3.5 rounded-xl font-medium transition-all"
            >
              <Github size={20} />
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
      <section className="max-w-4xl mx-auto px-6 pb-24">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="relative rounded-2xl overflow-hidden shadow-2xl shadow-indigo-500/10 border border-white/10"
        >
          <div className="absolute inset-0 bg-zinc-900/80 backdrop-blur-sm z-0" />

          {/* Fake Header */}
          <div className="relative z-10 flex items-center gap-2 px-4 py-4 border-b border-white/5 bg-white/5">
            <div className="flex gap-2">
              <div className="w-3 h-3 rounded-full bg-red-500/80" />
              <div className="w-3 h-3 rounded-full bg-amber-500/80" />
              <div className="w-3 h-3 rounded-full bg-emerald-500/80" />
            </div>
          </div>

          {/* Demo content */}
          <div className="relative z-10 p-6 space-y-6 min-h-[300px] flex flex-col justify-center">
            {/* User question */}
            <div className="flex justify-end items-center gap-3">
              <div className="bg-gradient-to-br from-indigo-600 to-violet-600 text-white px-5 py-3 rounded-2xl rounded-tr-sm shadow-lg shadow-indigo-500/20">
                What is the main entry point?
              </div>
              <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center shadow-lg">
                <div className="text-white text-xs font-bold">You</div>
              </div>
            </div>

            {/* AI response */}
            <div className="flex items-start gap-4 max-w-[85%]">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-purple-500 to-indigo-500 flex items-center justify-center shadow-lg flex-shrink-0">
                <Sparkles size={14} className="text-white" />
              </div>
              <div className="space-y-3">
                <div className="text-zinc-300 leading-relaxed">
                  The main entry point is <code className="bg-white/10 text-indigo-300 px-1.5 py-0.5 rounded border border-white/5">src/app/layout.tsx</code>
                </div>
                <div className="bg-black/40 border border-white/10 rounded-xl overflow-hidden">
                  <div className="px-4 py-2 bg-white/5 border-b border-white/5 flex items-center justify-between">
                    <span className="text-xs text-indigo-300 font-mono">src/app/layout.tsx</span>
                  </div>
                  <pre className="p-4 text-xs font-mono text-zinc-400 overflow-x-auto">
                    {`export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>{children}</body>
    </html>
  )
}`}
                  </pre>
                </div>
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
