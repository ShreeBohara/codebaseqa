'use client';

import { motion } from 'framer-motion';
import { useMemo } from 'react';
import { format, subDays, eachDayOfInterval } from 'date-fns';

interface ActivityHeatmapProps {
    data: Record<string, number>; // date "YYYY-MM-DD" -> count
}

export function ActivityHeatmap({ data }: ActivityHeatmapProps) {
    const daysToShow = 365; // Show last year

    // Generate dates
    const dates = useMemo(() => {
        const today = new Date();
        const start = subDays(today, daysToShow);
        return eachDayOfInterval({ start, end: today });
    }, []);

    // Calculate max value for color intensity scaling
    const maxCount = useMemo(() => {
        const counts = Object.values(data);
        return Math.max(...counts, 4); // Min 4 to avoid too intense colors for low activity
    }, [data]);

    const getColor = (count: number) => {
        if (count === 0) return 'bg-zinc-800/50';
        const intensity = Math.min(count / maxCount, 1);
        if (intensity < 0.25) return 'bg-emerald-900/80';
        if (intensity < 0.5) return 'bg-emerald-700';
        if (intensity < 0.75) return 'bg-emerald-500';
        return 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)]';
    };

    return (
        <div className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-6">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                Activity Log
                <span className="text-xs font-normal text-zinc-500 bg-zinc-800 px-2 py-0.5 rounded-full">
                    Last 365 Days
                </span>
            </h3>

            <div className="overflow-x-auto pb-2 custom-scrollbar">
                <div className="flex gap-1 min-w-max">
                    {/* Weeks (simplified logical grouping for visual) */}
                    {Array.from({ length: 53 }).map((_, weekIdx) => (
                        <div key={weekIdx} className="flex flex-col gap-1">
                            {Array.from({ length: 7 }).map((_, dayIdx) => {
                                const dateIndex = weekIdx * 7 + dayIdx;
                                if (dateIndex >= dates.length) return null;

                                const date = dates[dateIndex];
                                const dateStr = format(date, 'yyyy-MM-dd');
                                const count = data[dateStr] || 0;

                                return (
                                    <motion.div
                                        key={dateStr}
                                        initial={{ opacity: 0 }}
                                        animate={{ opacity: 1 }}
                                        transition={{ delay: dateIndex * 0.001 }}
                                        className={`w-3 h-3 rounded-sm ${getColor(count)}`}
                                        title={`${dateStr}: ${count} activities`}
                                    />
                                );
                            })}
                        </div>
                    ))}
                </div>
            </div>

            <div className="flex items-center gap-2 text-xs text-zinc-500 mt-3 justify-end">
                <span>Less</span>
                <div className="flex gap-1">
                    <div className="w-3 h-3 rounded-sm bg-zinc-800/50" />
                    <div className="w-3 h-3 rounded-sm bg-emerald-900/80" />
                    <div className="w-3 h-3 rounded-sm bg-emerald-700" />
                    <div className="w-3 h-3 rounded-sm bg-emerald-500" />
                    <div className="w-3 h-3 rounded-sm bg-emerald-400" />
                </div>
                <span>More</span>
            </div>
        </div>
    );
}
