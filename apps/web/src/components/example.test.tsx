import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'

describe('Example Test', () => {
    it('should pass', () => {
        expect(1 + 1).toBe(2)
    })

    it('should render component', () => {
        render(<div>Hello Test</div>)
        expect(screen.getByText('Hello Test')).toBeInTheDocument()
    })
})
