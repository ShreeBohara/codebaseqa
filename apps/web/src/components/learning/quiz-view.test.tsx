import { describe, it, expect, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QuizView } from './quiz-view'
import { api } from '@/lib/api-client'

vi.mock('@/lib/api-client', () => ({
    api: {
        submitQuizResult: vi.fn(),
    },
}))

vi.mock('canvas-confetti', () => ({
    default: vi.fn(),
}))

vi.mock('framer-motion', () => ({
    motion: {
        div: ({ children, ...props }: { children?: React.ReactNode; [key: string]: unknown }) => <div {...props}>{children}</div>,
    },
    AnimatePresence: ({ children }: { children?: React.ReactNode }) => <>{children}</>,
}))

describe('QuizView', () => {
    it('submits quiz score to backend and surfaces backend result', async () => {
        const onClose = vi.fn()
        const onResultSubmitted = vi.fn()
        const quiz = {
            lesson_id: 'lesson-1',
            questions: [
                {
                    id: 'q1',
                    text: 'What is 2 + 2?',
                    options: ['3', '4', '5', '6'],
                    correct_option_index: 1,
                    explanation: '2 + 2 equals 4',
                },
            ],
        }

        vi.mocked(api.submitQuizResult).mockResolvedValueOnce({
            xp_gained: { amount: 100, reason: 'quiz_perfect', bonus: 0 },
            stats: {
                total_xp: 100,
                level: {
                    level: 1,
                    title: 'Newcomer',
                    icon: '🌱',
                    current_xp: 100,
                    xp_for_next_level: 200,
                    xp_progress: 0.5,
                },
                streak: {
                    current: 1,
                    longest: 1,
                    active_today: true,
                },
                lessons_completed: 1,
                quizzes_passed: 1,
                challenges_completed: 0,
                perfect_quizzes: 1,
            },
            is_pass: true,
            is_perfect: true,
        })

        render(
            <QuizView
                repoId="repo-1"
                quiz={quiz}
                onClose={onClose}
                onResultSubmitted={onResultSubmitted}
            />
        )

        fireEvent.click(screen.getByText('4'))
        fireEvent.click(screen.getByText('Finish Quiz'))

        await waitFor(() => {
            expect(api.submitQuizResult).toHaveBeenCalledWith('repo-1', 'lesson-1', 1)
        })

        expect(onResultSubmitted).toHaveBeenCalledOnce()
        expect(screen.getByText('Quiz Complete!')).toBeInTheDocument()
        expect(screen.getByText('Perfect score! +100 XP')).toBeInTheDocument()
    })
})
