import { describe, it, expect, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { ChallengeView } from './ChallengeView'
import { api } from '@/lib/api-client'

vi.mock('@/lib/api-client', () => ({
    api: {
        validateChallenge: vi.fn(),
    },
}))

vi.mock('framer-motion', () => ({
    motion: {
        div: ({ children, ...props }: { children?: React.ReactNode; [key: string]: unknown }) => <div {...props}>{children}</div>,
    },
    AnimatePresence: ({ children }: { children?: React.ReactNode }) => <>{children}</>,
}))

describe('ChallengeView', () => {
    it('validates bug hunt answers through backend API', async () => {
        const challenge = {
            id: 'challenge-1',
            lesson_id: 'lesson-1',
            challenge_type: 'bug_hunt' as const,
            data: {
                description: 'Find the bug',
                code_snippet: 'const a = 1;\nconst b = a + 1;\nreturn b;',
                bug_line: 2,
                bug_description: 'Wrong increment',
                hint: 'Check arithmetic',
            },
            completed: false,
            used_hint: false,
        }

        const validationResult = {
            correct: true,
            correct_line: 2,
            explanation: 'Wrong increment',
            xp_earned: 75,
            xp_gained: { amount: 75, reason: 'challenge_complete', bonus: 0 },
        }

        vi.mocked(api.validateChallenge).mockResolvedValueOnce(validationResult)

        const onComplete = vi.fn()

        render(
            <ChallengeView
                repoId="repo-1"
                challenge={challenge}
                onComplete={onComplete}
                onClose={() => {}}
            />
        )

        fireEvent.click(screen.getByText('const b = a + 1;'))
        fireEvent.click(screen.getByText('Submit Answer'))

        await waitFor(() => {
            expect(api.validateChallenge).toHaveBeenCalledWith(
                'repo-1',
                'bug_hunt',
                challenge,
                2,
                false
            )
        })

        expect(onComplete).toHaveBeenCalledWith(validationResult, false)
        expect(screen.getByText('Correct! +75 XP')).toBeInTheDocument()
    })
})
