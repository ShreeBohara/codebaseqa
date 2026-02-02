'use client';

import { useState, useRef, useEffect, FormEvent } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { api, ChatMessage } from '@/lib/api-client';
import ReactMarkdown from 'react-markdown';
import { Send, Loader2, FileCode, ChevronDown, Copy, Check, Sparkles } from 'lucide-react';

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

const suggestedQuestions = [
    "What is the main entry point?",
    "Explain the project structure",
    "How does authentication work?",
    "What technologies is this built with?",
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
            setMessages((prev) => prev.map((m) => m.id === assistantMessage.id ? { ...m, content: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`, isStreaming: false } : m));
        } finally {
            setIsLoading(false);
        }
    };

    const toggleSources = (messageId: string) => {
        setExpandedSources((prev) => ({ ...prev, [messageId]: !prev[messageId] }));
    };

    return (
        <div className="flex flex-col h-full bg-zinc-950">
            {/* Messages */}
            <div className="flex-1 overflow-y-auto">
                <div className="max-w-2xl mx-auto px-4 py-8">
                    <AnimatePresence mode="popLayout">
                        {messages.length === 0 ? (
                            // Empty State with color
                            <motion.div
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                className="flex flex-col items-center justify-center min-h-[50vh]"
                            >
                                {/* Colored icon */}
                                <div className="w-14 h-14 rounded-2xl bg-indigo-500/10 flex items-center justify-center mb-6">
                                    <Sparkles size={28} className="text-indigo-400" />
                                </div>

                                <h1 className="text-2xl font-medium text-white mb-2">How can I help?</h1>
                                <p className="text-zinc-500 mb-8 text-sm">
                                    Ask about <span className="text-indigo-400">{repoName}</span>
                                </p>

                                {/* Colored suggestion pills */}
                                <div className="flex flex-wrap gap-2 justify-center max-w-md">
                                    {suggestedQuestions.map((q, i) => (
                                        <button
                                            key={i}
                                            onClick={() => { setInput(q); inputRef.current?.focus(); }}
                                            className="px-3 py-1.5 text-sm text-zinc-300 bg-zinc-900 border border-zinc-800 rounded-full hover:border-indigo-500/50 hover:text-white transition-all"
                                        >
                                            {q}
                                        </button>
                                    ))}
                                </div>
                            </motion.div>
                        ) : (
                            // Messages
                            <div className="space-y-6">
                                {messages.map((message) => (
                                    <motion.div
                                        key={message.id}
                                        initial={{ opacity: 0, y: 10 }}
                                        animate={{ opacity: 1, y: 0 }}
                                    >
                                        {message.role === 'user' ? (
                                            // User message - INDIGO background
                                            <div className="flex justify-end">
                                                <div className="bg-indigo-600 text-white px-4 py-2.5 rounded-2xl rounded-br-sm max-w-[80%]">
                                                    {message.content}
                                                </div>
                                            </div>
                                        ) : (
                                            // AI message
                                            <div>
                                                <div className="text-zinc-300 leading-relaxed">
                                                    {message.isStreaming && !message.content ? (
                                                        <div className="flex items-center gap-2">
                                                            <Loader2 size={16} className="animate-spin text-indigo-400" />
                                                            <span className="text-zinc-500">Thinking...</span>
                                                        </div>
                                                    ) : (
                                                        <div className="prose prose-invert prose-sm max-w-none">
                                                            <ReactMarkdown
                                                                components={{
                                                                    code({ className, children, ...props }) {
                                                                        const match = /language-(\w+)/.exec(className || '');
                                                                        const isInline = !match && String(children).length < 100 && !String(children).includes('\n');

                                                                        if (isInline) {
                                                                            return (
                                                                                <code className="bg-indigo-500/15 text-indigo-300 px-1.5 py-0.5 rounded text-sm font-mono" {...props}>
                                                                                    {children}
                                                                                </code>
                                                                            );
                                                                        }

                                                                        const code = String(children).replace(/\n$/, '');
                                                                        return (
                                                                            <div className="my-3 bg-zinc-900 rounded-lg border border-zinc-800 overflow-hidden not-prose">
                                                                                <div className="flex items-center justify-between px-3 py-2 border-b border-zinc-800 bg-zinc-800/50">
                                                                                    <span className="text-xs text-zinc-500">{match?.[1] || 'Code'}</span>
                                                                                    <CopyButton text={code} />
                                                                                </div>
                                                                                <pre className="p-3 overflow-x-auto m-0">
                                                                                    <code className={`text-sm text-zinc-300 ${className || ''}`} {...props}>
                                                                                        {children}
                                                                                    </code>
                                                                                </pre>
                                                                            </div>
                                                                        );
                                                                    },
                                                                    p: ({ children }) => <div className="mb-3 last:mb-0 text-zinc-300 leading-relaxed">{children}</div>,
                                                                    ul: ({ children }) => <ul className="list-disc pl-5 mb-3 space-y-1 text-zinc-300">{children}</ul>,
                                                                    ol: ({ children }) => <ol className="list-decimal pl-5 mb-3 space-y-1 text-zinc-300">{children}</ol>,
                                                                    strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
                                                                    a: ({ href, children }) => <a href={href} target="_blank" rel="noopener noreferrer" className="text-indigo-400 hover:text-indigo-300 underline underline-offset-2">{children}</a>
                                                                }}
                                                            >
                                                                {message.content}
                                                            </ReactMarkdown>
                                                        </div>
                                                    )}
                                                </div>

                                                {/* Sources */}
                                                {message.sources && message.sources.length > 0 && !message.isStreaming && (
                                                    <div className="mt-3">
                                                        <button
                                                            onClick={() => toggleSources(message.id)}
                                                            className="flex items-center gap-1.5 text-xs text-zinc-500 hover:text-indigo-400 transition-colors"
                                                        >
                                                            <FileCode size={12} />
                                                            {message.sources.length} sources
                                                            <ChevronDown size={12} className={`transition-transform ${expandedSources[message.id] ? 'rotate-180' : ''}`} />
                                                        </button>

                                                        <AnimatePresence>
                                                            {expandedSources[message.id] && (
                                                                <motion.div
                                                                    initial={{ height: 0, opacity: 0 }}
                                                                    animate={{ height: 'auto', opacity: 1 }}
                                                                    exit={{ height: 0, opacity: 0 }}
                                                                    className="overflow-hidden"
                                                                >
                                                                    <div className="mt-2 space-y-2">
                                                                        {message.sources.map((src, i) => (
                                                                            <div key={i} className="bg-zinc-900 rounded-lg border border-zinc-800 text-xs">
                                                                                <div className="px-3 py-1.5 border-b border-zinc-800 text-indigo-400 font-mono">
                                                                                    {src.file}:{src.start_line}
                                                                                </div>
                                                                                <pre className="p-2 text-zinc-500 overflow-x-auto">{src.content}</pre>
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
                                    </motion.div>
                                ))}
                                <div ref={messagesEndRef} />
                            </div>
                        )}
                    </AnimatePresence>
                </div>
            </div>

            {/* Input with indigo send button */}
            <div className="border-t border-zinc-800 bg-zinc-950 p-4">
                <form onSubmit={handleSubmit} className="max-w-2xl mx-auto">
                    <div className="flex items-end gap-2 bg-zinc-900 border border-zinc-800 rounded-xl p-2 focus-within:border-indigo-500/50 transition-colors">
                        <textarea
                            ref={inputRef}
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSubmit(e); } }}
                            placeholder="Ask a question..."
                            className="flex-1 bg-transparent text-white px-2 py-2 resize-none focus:outline-none placeholder:text-zinc-600 min-h-[40px] max-h-[120px]"
                            rows={1}
                            disabled={isLoading}
                            onInput={(e) => {
                                const t = e.target as HTMLTextAreaElement;
                                t.style.height = 'auto';
                                t.style.height = Math.min(t.scrollHeight, 120) + 'px';
                            }}
                        />
                        <button
                            type="submit"
                            disabled={isLoading || !input.trim()}
                            className="bg-indigo-600 hover:bg-indigo-700 text-white p-2 rounded-lg disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                        >
                            {isLoading ? <Loader2 size={18} className="animate-spin" /> : <Send size={18} />}
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
