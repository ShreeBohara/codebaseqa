'use client';

import { useState, useRef, useEffect, FormEvent } from 'react';
import { api, StreamingChunk, ChatMessage } from '@/lib/api-client';
import ReactMarkdown from 'react-markdown';
import { Send, Loader2, FileCode, ChevronDown } from 'lucide-react';

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

export function ChatInterface({ sessionId, repoName, initialMessages = [] }: ChatInterfaceProps) {
    const [messages, setMessages] = useState<Message[]>(() =>
        initialMessages.map((m) => ({
            id: m.id,
            role: m.role,
            content: m.content,
        }))
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

        const userMessage: Message = {
            id: `user-${Date.now()}`,
            role: 'user',
            content: input.trim(),
        };

        setMessages((prev) => [...prev, userMessage]);
        setInput('');
        setIsLoading(true);

        const assistantMessage: Message = {
            id: `assistant-${Date.now()}`,
            role: 'assistant',
            content: '',
            isStreaming: true,
        };

        setMessages((prev) => [...prev, assistantMessage]);

        try {
            for await (const chunk of api.streamChat(sessionId, userMessage.content)) {
                if (chunk.type === 'sources') {
                    setMessages((prev) =>
                        prev.map((m) =>
                            m.id === assistantMessage.id ? { ...m, sources: chunk.sources } : m
                        )
                    );
                } else if (chunk.type === 'content') {
                    setMessages((prev) =>
                        prev.map((m) =>
                            m.id === assistantMessage.id
                                ? { ...m, content: m.content + (chunk.content || '') }
                                : m
                        )
                    );
                } else if (chunk.type === 'done') {
                    setMessages((prev) =>
                        prev.map((m) =>
                            m.id === assistantMessage.id ? { ...m, isStreaming: false } : m
                        )
                    );
                } else if (chunk.type === 'error') {
                    setMessages((prev) =>
                        prev.map((m) =>
                            m.id === assistantMessage.id
                                ? { ...m, content: `Error: ${chunk.error}`, isStreaming: false }
                                : m
                        )
                    );
                }
            }
        } catch (error) {
            setMessages((prev) =>
                prev.map((m) =>
                    m.id === assistantMessage.id
                        ? { ...m, content: `Error: ${error instanceof Error ? error.message : 'Unknown error'}`, isStreaming: false }
                        : m
                )
            );
        } finally {
            setIsLoading(false);
        }
    };

    const toggleSources = (messageId: string) => {
        setExpandedSources((prev) => ({
            ...prev,
            [messageId]: !prev[messageId],
        }));
    };

    return (
        <div className="flex flex-col h-full bg-zinc-950">
            {/* Header */}
            <div className="flex-shrink-0 border-b border-zinc-800 px-6 py-4">
                <h2 className="text-lg font-semibold text-white">Chat with {repoName}</h2>
                <p className="text-sm text-zinc-400">Ask questions about the codebase</p>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
                {messages.length === 0 && (
                    <div className="text-center text-zinc-500 py-12">
                        <p className="text-lg">Start asking questions about the codebase</p>
                        <p className="text-sm mt-2">Try: "What is the main entry point?" or "How does authentication work?"</p>
                    </div>
                )}

                {messages.map((message) => (
                    <div
                        key={message.id}
                        className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                        <div
                            className={`max-w-[80%] rounded-2xl px-5 py-3 ${message.role === 'user'
                                    ? 'bg-blue-600 text-white'
                                    : 'bg-zinc-800 text-zinc-100'
                                }`}
                        >
                            {message.role === 'assistant' ? (
                                <div className="prose prose-invert prose-sm max-w-none">
                                    <ReactMarkdown
                                        components={{
                                            code({ className, children, ...props }) {
                                                const match = /language-(\w+)/.exec(className || '');
                                                const isInline = !match;
                                                return isInline ? (
                                                    <code className="bg-zinc-700 px-1.5 py-0.5 rounded text-sm" {...props}>
                                                        {children}
                                                    </code>
                                                ) : (
                                                    <pre className="bg-zinc-900 p-4 rounded-lg overflow-x-auto">
                                                        <code className={className} {...props}>
                                                            {children}
                                                        </code>
                                                    </pre>
                                                );
                                            },
                                        }}
                                    >
                                        {message.content || (message.isStreaming ? '...' : '')}
                                    </ReactMarkdown>

                                    {/* Sources */}
                                    {message.sources && message.sources.length > 0 && (
                                        <div className="mt-4 border-t border-zinc-700 pt-3">
                                            <button
                                                onClick={() => toggleSources(message.id)}
                                                className="flex items-center gap-2 text-sm text-zinc-400 hover:text-zinc-200"
                                            >
                                                <FileCode size={16} />
                                                {message.sources.length} source{message.sources.length > 1 ? 's' : ''}
                                                <ChevronDown
                                                    size={16}
                                                    className={`transition-transform ${expandedSources[message.id] ? 'rotate-180' : ''}`}
                                                />
                                            </button>
                                            {expandedSources[message.id] && (
                                                <div className="mt-2 space-y-2">
                                                    {message.sources.map((source, i) => (
                                                        <div key={i} className="bg-zinc-900 rounded-lg p-3 text-xs">
                                                            <div className="flex items-center justify-between mb-1">
                                                                <span className="text-zinc-300 font-mono">{source.file}</span>
                                                                <span className="text-zinc-500">
                                                                    L{source.start_line}-{source.end_line}
                                                                </span>
                                                            </div>
                                                            <pre className="text-zinc-400 overflow-x-auto whitespace-pre-wrap">
                                                                {source.content}
                                                            </pre>
                                                        </div>
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            ) : (
                                <p>{message.content}</p>
                            )}
                        </div>
                    </div>
                ))}
                <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <form onSubmit={handleSubmit} className="flex-shrink-0 border-t border-zinc-800 p-4">
                <div className="flex gap-3">
                    <textarea
                        ref={inputRef}
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey) {
                                e.preventDefault();
                                handleSubmit(e);
                            }
                        }}
                        placeholder="Ask about the codebase..."
                        className="flex-1 bg-zinc-800 text-white rounded-xl px-4 py-3 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 placeholder:text-zinc-500"
                        rows={1}
                        disabled={isLoading}
                    />
                    <button
                        type="submit"
                        disabled={isLoading || !input.trim()}
                        className="bg-blue-600 text-white rounded-xl px-4 py-3 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                        {isLoading ? <Loader2 size={20} className="animate-spin" /> : <Send size={20} />}
                    </button>
                </div>
            </form>
        </div>
    );
}
