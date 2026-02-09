import { describe, it, expect, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { SyllabusView } from './syllabus-view'
import { Syllabus } from '@/lib/api-client'

vi.mock('framer-motion', () => ({
    motion: {
        div: ({ children, ...props }: { children?: React.ReactNode; [key: string]: unknown }) => <div {...props}>{children}</div>,
        button: ({ children, whileHover, ...props }: { children?: React.ReactNode; whileHover?: unknown; [key: string]: unknown }) => {
            void whileHover
            return <button {...props}>{children}</button>
        },
    },
    AnimatePresence: ({ children }: { children?: React.ReactNode }) => <>{children}</>,
}))

const syllabus: Syllabus = {
    repo_id: 'repo-1',
    persona: 'new_hire',
    title: 'Track',
    description: 'Description',
    cache_info: {
        source: 'cache',
        generated_at: '2026-02-09T10:00:00Z',
        expires_at: '2026-02-16T10:00:00Z',
    },
    modules: [
        {
            title: 'Module 1',
            description: 'M1',
            lessons: [
                {
                    id: 'lesson-1',
                    title: 'Lesson 1',
                    description: 'L1',
                    type: 'concept',
                    estimated_minutes: 10,
                },
                {
                    id: 'lesson-2',
                    title: 'Lesson 2',
                    description: 'L2',
                    type: 'concept',
                    estimated_minutes: 10,
                },
            ],
        },
    ],
}

describe('SyllabusView', () => {
    it('triggers track refresh callback', async () => {
        const onRefreshTrack = vi.fn()
        render(
            <SyllabusView
                syllabus={syllabus}
                selectedPersona="new_hire"
                onRefreshTrack={onRefreshTrack}
                onLessonSelect={() => {}}
                completedLessons={new Set()}
            />
        )

        fireEvent.click(screen.getByText('Regenerate Track'))
        await waitFor(() => {
            expect(onRefreshTrack).toHaveBeenCalledOnce()
        })
    })

    it('passes module context when selecting a lesson', async () => {
        const onLessonSelect = vi.fn()
        render(
            <SyllabusView
                syllabus={syllabus}
                selectedPersona="new_hire"
                onLessonSelect={onLessonSelect}
                completedLessons={new Set()}
            />
        )

        fireEvent.click(screen.getByText('Lesson 1'))
        expect(onLessonSelect).toHaveBeenCalledWith(expect.objectContaining({ id: 'lesson-1' }), 'module-1')
    })
})
