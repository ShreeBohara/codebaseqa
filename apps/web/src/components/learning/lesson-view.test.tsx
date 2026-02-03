import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { LessonView } from './lesson-view'
import { api } from '@/lib/api-client'

// Mock dependencies
vi.mock('@/lib/api-client', () => ({
    api: {
        getRepoFileContent: vi.fn(),
        generateQuiz: vi.fn(),
        completeLesson: vi.fn(),
    }
}))

vi.mock('canvas-confetti', () => ({
    default: vi.fn()
}))

// Mock Framer Motion to avoid animation issues in tests
vi.mock('framer-motion', () => ({
    motion: {
        div: ({ children, ...props }: { children?: React.ReactNode; [key: string]: unknown }) => <div {...props}>{children}</div>,
    },
    AnimatePresence: ({ children }: { children?: React.ReactNode }) => <>{children}</>,
}))

// Mock child components to simplify testing
vi.mock('./quiz-view', () => ({
    QuizView: ({ onClose }: { onClose: () => void }) => (
        <div data-testid="quiz-view">
            <h1>Quiz Interface</h1>
            <button onClick={onClose}>Close Quiz</button>
        </div>
    )
}))

vi.mock('./ChallengeView', () => ({
    ChallengeView: () => <div data-testid="challenge-view">Challenge Interface</div>
}))

vi.mock('./MermaidDiagram', () => ({
    MermaidDiagram: () => <div data-testid="mermaid-diagram">Mermaid Diagram</div>
}))

const mockContent = {
    id: 'lesson-1',
    title: 'Test Lesson',
    content_markdown: '# Hello World\nThis is a test lesson.',
    code_references: [
        {
            file_path: 'src/main.py',
            start_line: 1,
            end_line: 5,
            description: 'Main entry point'
        }
    ],
    diagram_mermaid: 'graph TD; A-->B;'
}

describe('LessonView', () => {
    const mockOnClose = vi.fn()
    const mockOnComplete = vi.fn()

    beforeEach(() => {
        vi.clearAllMocks()
        // Mock scrollIntoView since JSDOM doesn't support it
        window.HTMLElement.prototype.scrollIntoView = vi.fn()
    })

    it('renders lesson title and content', () => {
        render(
            <LessonView
                repoId="repo-123"
                content={mockContent}
                onClose={mockOnClose}
                onComplete={mockOnComplete}
            />
        )

        expect(screen.getByText('Test Lesson')).toBeInTheDocument()
        expect(screen.getByText('Hello World')).toBeInTheDocument()
        expect(screen.getByText('This is a test lesson.')).toBeInTheDocument()
    })

    it('loads and displays file content', async () => {
        const mockFileContent = 'print("Hello Python")'
        vi.mocked(api.getRepoFileContent).mockResolvedValueOnce({ content: mockFileContent })

        render(
            <LessonView
                repoId="repo-123"
                content={mockContent}
                onClose={mockOnClose}
            />
        )

        await waitFor(() => {
            expect(api.getRepoFileContent).toHaveBeenCalledWith('repo-123', 'src/main.py')
        })

        expect(screen.getByText('print("Hello Python")')).toBeInTheDocument()
    })

    it('handles quiz generation', async () => {
        const mockQuiz = { lesson_id: 'lesson-1', questions: [] }
        vi.mocked(api.generateQuiz).mockResolvedValueOnce(mockQuiz)

        render(
            <LessonView
                repoId="repo-123"
                content={mockContent}
                onClose={mockOnClose}
            />
        )

        const quizBtn = screen.getByText('Take Quiz')
        fireEvent.click(quizBtn)

        expect(screen.getByText('Generating Quiz...')).toBeInTheDocument()

        await waitFor(() => {
            expect(api.generateQuiz).toHaveBeenCalled()
        })

        expect(screen.getByTestId('quiz-view')).toBeInTheDocument()
    })

    it('handles completion', async () => {
        vi.mocked(api.completeLesson).mockResolvedValueOnce({
            xp_gained: { amount: 100, reason: 'Completed' },
            stats: {} as Record<string, unknown>
        })

        render(
            <LessonView
                repoId="repo-123"
                content={mockContent}
                onClose={mockOnClose}
                onComplete={mockOnComplete}
            />
        )

        const finishBtn = screen.getByText('Finish Lesson')
        fireEvent.click(finishBtn)

        await waitFor(() => {
            expect(api.completeLesson).toHaveBeenCalled()
        })

        expect(mockOnComplete).toHaveBeenCalledWith({ amount: 100, reason: 'Completed' })
        expect(mockOnClose).toHaveBeenCalled()
    })
})
