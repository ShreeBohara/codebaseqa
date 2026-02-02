import { Syllabus, Module, Lesson } from '@/lib/api-client';
import { motion } from 'framer-motion';
import { BookOpen, Code, Terminal, Clock, ChevronRight, Play } from 'lucide-react';

interface SyllabusViewProps {
    syllabus: Syllabus;
    onLessonSelect: (lesson: Lesson) => void;
}

export function SyllabusView({ syllabus, onLessonSelect }: SyllabusViewProps) {
    return (
        <div className="space-y-8">
            {/* Header */}
            <div className="text-center mb-10">
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="inline-block px-4 py-1.5 rounded-full bg-indigo-500/10 text-indigo-400 text-sm font-medium mb-4"
                >
                    {syllabus.persona.replace('_', ' ').toUpperCase()} TRACK
                </motion.div>

                <h2 className="text-3xl font-bold text-white mb-3">{syllabus.title}</h2>
                <p className="text-zinc-400 max-w-2xl mx-auto">{syllabus.description}</p>
            </div>

            {/* Modules */}
            <div className="space-y-6 max-w-3xl mx-auto">
                {syllabus.modules.map((module, mIdx) => (
                    <motion.div
                        key={mIdx}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: mIdx * 0.1 }}
                        className="group"
                    >
                        {/* Timeline Connector */}
                        {mIdx !== syllabus.modules.length - 1 && (
                            <div className="absolute left-8 ml-px h-full w-0.5 bg-zinc-800 -z-10 translate-y-8" />
                        )}

                        <div className="bg-zinc-900/50 border border-zinc-800 rounded-xl overflow-hidden group-hover:border-zinc-700 transition-colors">
                            <div className="p-5 border-b border-zinc-800/50 bg-zinc-900/30">
                                <div className="flex items-center gap-3">
                                    <div className="w-8 h-8 rounded-full bg-zinc-800 flex items-center justify-center text-zinc-400 font-mono text-sm border border-zinc-700">
                                        {mIdx + 1}
                                    </div>
                                    <div>
                                        <h3 className="font-semibold text-zinc-200">{module.title}</h3>
                                        <p className="text-sm text-zinc-500">{module.description}</p>
                                    </div>
                                </div>
                            </div>

                            <div className="divide-y divide-zinc-800/50">
                                {module.lessons.map((lesson, lIdx) => (
                                    <LessonRow key={lesson.id} lesson={lesson} index={lIdx} onClick={() => onLessonSelect(lesson)} />
                                ))}
                            </div>
                        </div>
                    </motion.div>
                ))}
            </div>
        </div>
    );
}

function LessonRow({ lesson, index, onClick }: { lesson: Lesson; index: number; onClick: () => void }) {
    const Icon = lesson.type === 'concept' ? BookOpen :
        lesson.type === 'code_tour' ? Code : Terminal;

    return (
        <div
            onClick={onClick}
            className="p-4 flex items-center gap-4 hover:bg-zinc-800/30 transition-colors group/lesson cursor-pointer"
        >
            <div className="w-8 flex justify-center">
                {/* Placeholder for status checkbox */}
                <div className="w-2 h-2 rounded-full bg-zinc-800 group-hover/lesson:bg-indigo-500 transition-colors" />
            </div>

            <div className={`p-2 rounded-lg bg-zinc-900/50 text-zinc-500 group-hover/lesson:text-indigo-400 transition-colors`}>
                <Icon size={16} />
            </div>

            <div className="flex-1">
                <h4 className="text-sm font-medium text-zinc-300 group-hover/lesson:text-white transition-colors">
                    {lesson.title}
                </h4>
                <p className="text-xs text-zinc-500">{lesson.description}</p>
            </div>

            <div className="flex items-center gap-4">
                <div className="flex items-center gap-1.5 text-xs text-zinc-600">
                    <Clock size={12} />
                    {lesson.estimated_minutes}m
                </div>

                <button className="p-2 rounded-lg text-zinc-600 hover:bg-indigo-500 hover:text-white transition-all opacity-0 group-hover/lesson:opacity-100">
                    <Play size={14} fill="currentColor" />
                </button>
            </div>
        </div>
    );
}
