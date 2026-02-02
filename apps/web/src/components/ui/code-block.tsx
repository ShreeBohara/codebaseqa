'use client';

import { useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Copy, Check, FileCode } from 'lucide-react';
import { motion } from 'framer-motion';

interface CodeBlockProps {
    code: string;
    language?: string;
    filename?: string;
    startLine?: number;
    endLine?: number;
}

export function CodeBlock({ code, language = 'typescript', filename, startLine, endLine }: CodeBlockProps) {
    const [copied, setCopied] = useState(false);

    const handleCopy = async () => {
        await navigator.clipboard.writeText(code);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    // Detect language from filename if not provided
    const detectedLang = language || detectLanguage(filename || '');

    return (
        <motion.div
            className="code-block overflow-hidden my-3"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
        >
            {/* Header */}
            {filename && (
                <div className="flex items-center justify-between px-4 py-2 border-b border-white/5 bg-black/20">
                    <div className="flex items-center gap-2">
                        <FileCode size={14} className="text-[var(--neon-blue)]" />
                        <span className="text-sm font-mono text-[var(--text-secondary)]">
                            {filename}
                            {startLine && endLine && (
                                <span className="text-[var(--text-muted)]"> :{startLine}-{endLine}</span>
                            )}
                        </span>
                    </div>
                    <button
                        onClick={handleCopy}
                        className="p-1.5 rounded-md hover:bg-white/5 transition-colors"
                        title="Copy code"
                    >
                        {copied ? (
                            <Check size={14} className="text-[var(--neon-green)]" />
                        ) : (
                            <Copy size={14} className="text-[var(--text-muted)] hover:text-white" />
                        )}
                    </button>
                </div>
            )}

            {/* Code */}
            <SyntaxHighlighter
                language={detectedLang}
                style={vscDarkPlus}
                customStyle={{
                    margin: 0,
                    padding: '1rem',
                    background: 'transparent',
                    fontSize: '0.875rem',
                    lineHeight: 1.6,
                }}
                showLineNumbers={code.split('\n').length > 3}
                lineNumberStyle={{
                    minWidth: '2.5em',
                    paddingRight: '1em',
                    color: 'rgba(255,255,255,0.2)',
                    userSelect: 'none',
                }}
            >
                {code.trim()}
            </SyntaxHighlighter>
        </motion.div>
    );
}

function detectLanguage(filename: string): string {
    const ext = filename.split('.').pop()?.toLowerCase() || '';
    const langMap: Record<string, string> = {
        ts: 'typescript',
        tsx: 'tsx',
        js: 'javascript',
        jsx: 'jsx',
        py: 'python',
        go: 'go',
        rs: 'rust',
        java: 'java',
        json: 'json',
        md: 'markdown',
        css: 'css',
        html: 'html',
        yaml: 'yaml',
        yml: 'yaml',
        sh: 'bash',
    };
    return langMap[ext] || 'text';
}
