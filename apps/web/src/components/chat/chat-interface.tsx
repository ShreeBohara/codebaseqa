'use client';

import { useState, useRef, useEffect, FormEvent } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ApiError, api, ChatMessage } from '@/lib/api-client';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/cjs/styles/prism';
import { Send, Loader2, FileCode, ChevronDown, Copy, Check, Sparkles, BookOpen, Shield, Network, Zap, User } from 'lucide-react';

interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    sources?: Array<{
        file: string;
        content: string;
        start_line: number;
        end_line: number;
        score: number;
    }>;
    isStreaming?: boolean;
}

interface ChatInterfaceProps {
    sessionId: string;
    repoName: string;
    initialMessages?: ChatMessage[];
}

const suggestedActions = [
    {
        icon: <BookOpen className="w-5 h-5 text-indigo-400" />,
        title: "Explain Structure",
        prompt: "Explain the project structure and key components"
    },
    {
        icon: <Shield className="w-5 h-5 text-rose-400" />,
        title: "Auth Flow",
        prompt: "How does authentication and authorization work?"
    },
    {
        icon: <Network className="w-5 h-5 text-violet-400" />,
        title: "Tech Stack",
        prompt: "What technologies and libraries are used?"
    },
    {
        icon: <Zap className="w-5 h-5 text-amber-400" />,
        title: "Key Features",
        prompt: "What are the main features of this application?"
    }
];

export function ChatInterface({ sessionId, repoName, initialMessages = [] }: ChatInterfaceProps) {
    const [messages, setMessages] = useState<Message[]>(() =>
        initialMessages.map((m) => ({ id: m.id, role: m.role, content: m.content }))
    );
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [expandedSources, setExpandedSources] = useState<Record<string, boolean>>({});
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const inputRef = useRef<HTMLTextAreaElement>(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        if (!input.trim() || isLoading) return;

        const userMessage: Message = { id: `user-${Date.now()}`, role: 'user', content: input.trim() };
        setMessages((prev) => [...prev, userMessage]);
        setInput('');
        setIsLoading(true);

        const assistantMessage: Message = { id: `assistant-${Date.now()}`, role: 'assistant', content: '', isStreaming: true };
        setMessages((prev) => [...prev, assistantMessage]);

        try {
            for await (const chunk of api.streamChat(sessionId, userMessage.content)) {
                if (chunk.type === 'sources') {
                    setMessages((prev) => prev.map((m) => m.id === assistantMessage.id ? { ...m, sources: chunk.sources } : m));
                } else if (chunk.type === 'content') {
                    setMessages((prev) => prev.map((m) => m.id === assistantMessage.id ? { ...m, content: m.content + (chunk.content || '') } : m));
                } else if (chunk.type === 'done') {
                    setMessages((prev) => prev.map((m) => m.id === assistantMessage.id ? { ...m, isStreaming: false } : m));
                } else if (chunk.type === 'error') {
                    setMessages((prev) => prev.map((m) => m.id === assistantMessage.id ? { ...m, content: `Error: ${chunk.error}`, isStreaming: false } : m));
                }
            }
        } catch (error) {
            const message = (() => {
                if (error instanceof ApiError) {
                    if (error.status === 429) {
                        const retry = error.retryAfterSeconds ? ` Retry in ~${error.retryAfterSeconds}s.` : '';
                        return `Demo rate limit reached.${retry}`;
                    }
                    if (error.status === 503) {
                        return error.message || 'Demo is temporarily busy. Please retry shortly.';
                    }
                    return error.message;
                }
                return error instanceof Error ? error.message : 'Unknown error';
            })();
            setMessages((prev) =>
                prev.map((m) => (m.id === assistantMessage.id ? { ...m, content: `Error: ${message}`, isStreaming: false } : m))
            );
        } finally {
            setIsLoading(false);
        }
    };

    const toggleSources = (messageId: string) => {
        setExpandedSources((prev) => ({ ...prev, [messageId]: !prev[messageId] }));
    };

    return (
        <div className="flex flex-col h-full bg-zinc-950 relative">
            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-4 py-8 scroll-smooth">
                <div className="max-w-4xl mx-auto space-y-8">
                    <AnimatePresence mode="popLayout">
                        {messages.length === 0 ? (
                            // Empty State with color
                            // Modern Empty State
                            <motion.div
                                initial={{ opacity: 0, y: 20 }}
                                animate={{ opacity: 1, y: 0 }}
                                className="flex flex-col items-center justify-center min-h-[60vh] relative pb-32"
                            >
                                {/* Background Gradient Blob */}
                                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] bg-indigo-500/10 rounded-full blur-[100px] -z-10" />

                                {/* Hero Section */}
                                <div className="mb-12 text-center relative z-10">
                                    <div className="w-20 h-20 rounded-3xl bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-white/5 flex items-center justify-center mb-6 mx-auto shadow-xl shadow-indigo-500/10 backdrop-blur-sm">
                                        <Sparkles size={32} className="text-indigo-400" />
                                    </div>
                                    <h1 className="text-4xl font-bold text-white mb-3 tracking-tight">
                                        How can I help?
                                    </h1>
                                    <p className="text-zinc-400 text-lg">
                                        Ask me anything about <span className="text-indigo-400 font-medium">{repoName}</span>
                                    </p>
                                </div>

                                {/* Suggestion Grid */}
                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl w-full px-6">
                                    {suggestedActions.map((action, i) => (
                                        <motion.button
                                            key={i}
                                            initial={{ opacity: 0, scale: 0.95 }}
                                            animate={{ opacity: 1, scale: 1 }}
                                            transition={{ delay: i * 0.1 }}
                                            onClick={() => { setInput(action.prompt); inputRef.current?.focus(); }}
                                            className="group flex items-start gap-4 p-5 rounded-2xl bg-zinc-900/50 hover:bg-zinc-800/80 border border-zinc-800 hover:border-indigo-500/30 transition-all text-left backdrop-blur-sm"
                                        >
                                            <div className="p-3 rounded-xl bg-zinc-950/50 group-hover:scale-110 transition-transform duration-300">
                                                {action.icon}
                                            </div>
                                            <div>
                                                <h3 className="font-semibold text-zinc-200 group-hover:text-white transition-colors">
                                                    {action.title}
                                                </h3>
                                                <p className="text-sm text-zinc-500 group-hover:text-zinc-400">
                                                    {action.prompt}
                                                </p>
                                            </div>
                                        </motion.button>
                                    ))}
                                </div>
                                {/* Spacer to ensure prompts aren't hidden by the floating input on smaller screens */}
                                <div className="h-20 md:hidden" aria-hidden="true" />
                            </motion.div>
                        ) : (
                            // Messages
                            <div className="space-y-8">
                                {messages.map((message) => (
                                    <motion.div
                                        key={message.id}
                                        initial={{ opacity: 0, y: 20 }}
                                        animate={{ opacity: 1, y: 0 }}
                                        className={`flex gap-4 ${message.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}
                                    >
                                        {/* Avatar */}
                                        <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 shadow-sm ${message.role === 'user'
                                            ? 'bg-indigo-600'
                                            : 'bg-gradient-to-br from-purple-500 to-indigo-500'
                                            }`}>
                                            {message.role === 'user' ? (
                                                <User size={20} className="text-white" />
                                            ) : (
                                                <Sparkles size={20} className="text-white" />
                                            )}
                                        </div>

                                        {/* Message Bubble */}
                                        <div className={`flex-1 overflow-hidden ${message.role === 'user' ? 'text-right' : 'text-left'}`}>
                                            {/* Name Label */}
                                            <div className="text-xs text-zinc-500 mb-1.5 font-medium">
                                                {message.role === 'user' ? 'You' : 'Codebase AI'}
                                            </div>

                                            {message.role === 'user' ? (
                                                // User Message Bubble
                                                <div className="bg-gradient-to-br from-indigo-600 to-violet-600 border border-white/10 text-white px-5 py-3.5 rounded-2xl rounded-tr-sm inline-block text-left text-sm leading-relaxed shadow-lg shadow-indigo-900/20">
                                                    {message.content}
                                                </div>
                                            ) : (
                                                // AI Message Bubble - Premium styling
                                                <div className="bg-gradient-to-br from-zinc-900 to-zinc-900/80 border border-zinc-700/40 rounded-2xl rounded-tl-sm px-6 py-5 shadow-xl shadow-black/20 backdrop-blur-sm">
                                                    <div className="text-zinc-300 leading-relaxed">
                                                        {message.isStreaming && !message.content ? (
                                                            <div className="flex items-center gap-2 text-sm text-zinc-500">
                                                                <Loader2 size={14} className="animate-spin text-indigo-400" />
                                                                Thinking...
                                                            </div>
                                                        ) : (
                                                            <div className="prose prose-invert prose-sm max-w-none prose-p:leading-relaxed prose-pre:p-0 prose-pre:border-0 prose-pre:bg-transparent">
                                                                <ReactMarkdown
                                                                    components={{
                                                                        code({ className, children, ...props }) {
                                                                            const match = /language-(\w+)/.exec(className || '');
                                                                            const lang = match?.[1] || '';
                                                                            const isInline = !match && String(children).length < 100 && !String(children).includes('\n');

                                                                            if (isInline) {
                                                                                return (
                                                                                    <code className="bg-zinc-800/80 text-emerald-300 px-1.5 py-0.5 rounded text-[13px] font-mono" {...props}>
                                                                                        {children}
                                                                                    </code>
                                                                                );
                                                                            }

                                                                            const code = String(children).replace(/\n$/, '');
                                                                            return (
                                                                                <div className="my-4 rounded-xl border border-zinc-700/50 overflow-hidden not-prose shadow-lg">
                                                                                    <div className="flex items-center justify-between px-4 py-2.5 bg-zinc-800/80 border-b border-zinc-700/50">
                                                                                        <span className="text-xs text-zinc-400 font-medium uppercase tracking-wide">{lang || 'code'}</span>
                                                                                        <CopyButton text={code} />
                                                                                    </div>
                                                                                    <SyntaxHighlighter
                                                                                        language={lang || 'text'}
                                                                                        style={oneDark}
                                                                                        customStyle={{
                                                                                            margin: 0,
                                                                                            padding: '1rem',
                                                                                            background: '#1a1b26',
                                                                                            fontSize: '13px',
                                                                                            lineHeight: '1.6',
                                                                                        }}
                                                                                        showLineNumbers={code.split('\n').length > 3}
                                                                                        lineNumberStyle={{ color: '#4a5568', paddingRight: '1rem', minWidth: '2.5rem' }}
                                                                                    >
                                                                                        {code}
                                                                                    </SyntaxHighlighter>
                                                                                </div>
                                                                            );
                                                                        },
                                                                        p: ({ children }) => <div className="mb-4 last:mb-0 text-zinc-300">{children}</div>,
                                                                        ul: ({ children }) => <ul className="list-disc pl-5 mb-4 space-y-2 text-zinc-300">{children}</ul>,
                                                                        ol: ({ children }) => <ol className="list-decimal pl-5 mb-4 space-y-2 text-zinc-300">{children}</ol>,
                                                                        li: ({ children }) => <li className="pl-1">{children}</li>,
                                                                        strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
                                                                        a: ({ href, children }) => <a href={href} target="_blank" rel="noopener noreferrer" className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2 transition-colors">{children}</a>
                                                                    }}
                                                                >
                                                                    {message.content}
                                                                </ReactMarkdown>
                                                            </div>
                                                        )}
                                                    </div>

                                                    {/* Sources */}
                                                    {message.sources && message.sources.length > 0 && !message.isStreaming && (
                                                        <div className="mt-4 pt-3 border-t border-zinc-800/50">
                                                            <button
                                                                onClick={() => toggleSources(message.id)}
                                                                className="flex items-center gap-2 text-xs text-zinc-500 hover:text-indigo-400 transition-colors group"
                                                            >
                                                                <div className="p-1 rounded bg-zinc-800 group-hover:bg-indigo-500/10 transition-colors">
                                                                    <FileCode size={12} />
                                                                </div>
                                                                {message.sources.length} sources referenced
                                                                <ChevronDown size={12} className={`transition-transform duration-200 ${expandedSources[message.id] ? 'rotate-180' : ''}`} />
                                                            </button>

                                                            <AnimatePresence>
                                                                {expandedSources[message.id] && (
                                                                    <motion.div
                                                                        initial={{ height: 0, opacity: 0 }}
                                                                        animate={{ height: 'auto', opacity: 1 }}
                                                                        exit={{ height: 0, opacity: 0 }}
                                                                        className="overflow-hidden"
                                                                    >
                                                                        <div className="mt-3 space-y-3">
                                                                            {message.sources.map((src, i) => (
                                                                                <div key={i} className="bg-zinc-950/80 rounded-xl border border-zinc-700/40 text-xs overflow-hidden hover:border-indigo-500/30 transition-colors">
                                                                                    <div className="px-4 py-2.5 bg-zinc-800/50 border-b border-zinc-700/30 flex items-center justify-between">
                                                                                        <div className="flex items-center gap-2">
                                                                                            <FileCode size={14} className="text-indigo-400" />
                                                                                            <span className="text-zinc-200 font-medium">{src.file.split('/').pop()}</span>
                                                                                            <span className="text-zinc-500">L{src.start_line}-{src.end_line}</span>
                                                                                        </div>
                                                                                        <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 text-[10px] font-medium">
                                                                                            {(src.score * 100).toFixed(0)}% match
                                                                                        </span>
                                                                                    </div>
                                                                                    <pre className="p-3 text-zinc-400 overflow-x-auto font-mono text-[12px] leading-relaxed">{src.content}</pre>
                                                                                </div>
                                                                            ))}
                                                                        </div>
                                                                    </motion.div>
                                                                )}
                                                            </AnimatePresence>
                                                        </div>
                                                    )}
                                                </div>
                                            )}
                                        </div>
                                    </motion.div>
                                ))}
                                {/* Spacer to prevent overlap with floating input */}
                                <div className="h-40" aria-hidden="true" />
                                <div ref={messagesEndRef} />
                            </div>
                        )}
                    </AnimatePresence>
                </div>
            </div>

            {/* Floating Input Area */}
            <div className="absolute bottom-6 left-1/2 -translate-x-1/2 w-full max-w-4xl px-4 z-30">
                <form onSubmit={handleSubmit} className="relative group">
                    <div className="absolute -inset-0.5 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-2xl opacity-20 group-hover:opacity-40 transition-opacity blur duration-500" />

                    <div className="relative flex items-end gap-2 bg-zinc-900/90 backdrop-blur-xl border border-white/10 rounded-2xl p-2 shadow-2xl ring-1 ring-white/5">
                        <textarea
                            ref={inputRef}
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(e); } }}
                            placeholder="Ask a question..."
                            className="flex-1 bg-transparent text-white px-4 py-3 resize-none focus:outline-none placeholder:text-zinc-500 min-h-[48px] max-h-[160px] text-[15px] leading-relaxed"
                            rows={1}
                            disabled={isLoading}
                            onInput={(e) => {
                                const t = e.target as HTMLTextAreaElement;
                                t.style.height = 'auto';
                                t.style.height = Math.min(t.scrollHeight, 160) + 'px';
                            }}
                        />
                        <button
                            type="submit"
                            disabled={isLoading || !input.trim()}
                            className="mb-1 mr-1 bg-white text-black hover:bg-zinc-200 p-2.5 rounded-xl disabled:opacity-30 disabled:cursor-not-allowed transition-all shadow-lg shadow-white/5 active:scale-95"
                        >
                            {isLoading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} fill="currentColor" />}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}

function CopyButton({ text }: { text: string }) {
    const [copied, setCopied] = useState(false);
    return (
        <button
            onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 1500); }}
            className="text-zinc-500 hover:text-indigo-400 transition-colors"
        >
            {copied ? <Check size={12} className="text-green-400" /> : <Copy size={12} />}
        </button>
    );
}
