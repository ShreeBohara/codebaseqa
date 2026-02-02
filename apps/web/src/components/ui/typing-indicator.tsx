'use client';

import { motion } from 'framer-motion';

export function TypingIndicator() {
    return (
        <div className="flex items-center gap-1 px-4 py-3">
            {[0, 1, 2].map((i) => (
                <motion.div
                    key={i}
                    className="w-2 h-2 rounded-full bg-[var(--neon-blue)]"
                    initial={{ opacity: 0.4, y: 0 }}
                    animate={{
                        opacity: [0.4, 1, 0.4],
                        y: [0, -4, 0]
                    }}
                    transition={{
                        duration: 1,
                        repeat: Infinity,
                        delay: i * 0.15,
                        ease: "easeInOut"
                    }}
                />
            ))}
            <span className="ml-2 text-sm text-[var(--text-muted)]">Thinking...</span>
        </div>
    );
}
