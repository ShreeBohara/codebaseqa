import { Persona } from '@/lib/api-client';
import { motion } from 'framer-motion';
import { Check } from 'lucide-react';

interface PersonaSelectorProps {
    personas: Persona[];
    selectedId: string | null;
    onSelect: (id: string) => void;
    disabled?: boolean;
}

export function PersonaSelector({ personas, selectedId, onSelect, disabled }: PersonaSelectorProps) {
    return (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {personas.map((persona) => {
                const isSelected = selectedId === persona.id;

                return (
                    <motion.div
                        key={persona.id}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        onClick={() => !disabled && onSelect(persona.id)}
                        className={`
              relative p-5 rounded-xl border cursor-pointer transition-all
              ${isSelected
                                ? 'bg-indigo-500/10 border-indigo-500/50 shadow-lg shadow-indigo-500/10'
                                : 'bg-zinc-900/40 border-zinc-800 hover:border-zinc-700 hover:bg-zinc-900/60'}
              ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
            `}
                    >
                        <div className="flex items-start gap-4">
                            <div className={`
                w-12 h-12 rounded-lg flex items-center justify-center text-2xl
                ${isSelected ? 'bg-indigo-500/20' : 'bg-zinc-800/50'}
              `}>
                                {persona.icon || '🎓'}
                            </div>

                            <div className="flex-1">
                                <h3 className={`font-medium mb-1 ${isSelected ? 'text-indigo-300' : 'text-zinc-200'}`}>
                                    {persona.name}
                                </h3>
                                <p className="text-sm text-zinc-500 leading-relaxed">
                                    {persona.description}
                                </p>
                            </div>

                            {isSelected && (
                                <div className="absolute top-4 right-4 text-indigo-400">
                                    <Check size={18} />
                                </div>
                            )}
                        </div>
                    </motion.div>
                );
            })}
        </div>
    );
}
