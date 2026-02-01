import Link from 'next/link';
import { Code2, MessageCircle, Search, BookOpen, ArrowRight, Zap } from 'lucide-react';

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-zinc-950 via-zinc-900 to-zinc-950">
      {/* Navigation */}
      <nav className="border-b border-zinc-800 bg-zinc-950/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Code2 className="text-blue-500" size={28} />
            <span className="text-xl font-bold text-white">CodebaseQA</span>
          </div>
          <Link
            href="/repos"
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
          >
            Get Started
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-6xl mx-auto px-6 py-24 text-center">
        <div className="inline-flex items-center gap-2 bg-blue-500/10 border border-blue-500/20 rounded-full px-4 py-2 mb-6">
          <Zap size={16} className="text-blue-400" />
          <span className="text-sm text-blue-300">AI-Powered Codebase Understanding</span>
        </div>

        <h1 className="text-5xl md:text-6xl font-bold text-white leading-tight mb-6">
          Understand any codebase<br />
          <span className="bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
            in minutes
          </span>
        </h1>

        <p className="text-xl text-zinc-400 max-w-2xl mx-auto mb-10">
          Ask questions about any GitHub repository and get instant, accurate answers.
          Navigate complex codebases with AI-guided learning paths.
        </p>

        <div className="flex items-center justify-center gap-4">
          <Link
            href="/repos"
            className="flex items-center gap-2 bg-blue-600 text-white px-6 py-3 rounded-xl hover:bg-blue-700 transition-colors text-lg font-medium"
          >
            Start Exploring
            <ArrowRight size={20} />
          </Link>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-6xl mx-auto px-6 py-16">
        <div className="grid md:grid-cols-3 gap-6">
          <FeatureCard
            icon={<MessageCircle className="text-blue-400" size={28} />}
            title="Natural Language Q&A"
            description="Ask questions in plain English and get accurate, contextual answers about any codebase."
          />
          <FeatureCard
            icon={<Search className="text-purple-400" size={28} />}
            title="Semantic Code Search"
            description="Find relevant code using natural language queries. No need to remember exact function names."
          />
          <FeatureCard
            icon={<BookOpen className="text-green-400" size={28} />}
            title="Learning Paths"
            description="Get AI-generated guided tours through codebases to understand how everything connects."
          />
        </div>
      </section>

      {/* CTA */}
      <section className="max-w-6xl mx-auto px-6 py-16">
        <div className="bg-gradient-to-r from-blue-600/20 to-purple-600/20 border border-blue-500/20 rounded-2xl p-10 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">
            Ready to understand your codebase?
          </h2>
          <p className="text-zinc-400 mb-6">
            Index your first repository and start asking questions in seconds.
          </p>
          <Link
            href="/repos"
            className="inline-flex items-center gap-2 bg-white text-zinc-900 px-6 py-3 rounded-xl hover:bg-zinc-100 transition-colors font-medium"
          >
            Add Repository
            <ArrowRight size={20} />
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-zinc-800 py-8">
        <div className="max-w-6xl mx-auto px-6 text-center text-zinc-500 text-sm">
          <p>CodebaseQA • Self-hostable AI-powered codebase understanding</p>
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
  return (
    <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl p-6 hover:border-zinc-700 transition-colors">
      <div className="mb-4">{icon}</div>
      <h3 className="text-lg font-semibold text-white mb-2">{title}</h3>
      <p className="text-zinc-400 text-sm">{description}</p>
    </div>
  );
}
