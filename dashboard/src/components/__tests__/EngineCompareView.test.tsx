/**
 * EngineCompareView Component Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { EngineCompareView } from '../EngineCompareView'

const mockFetch = vi.fn()
global.fetch = mockFetch

describe('EngineCompareView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render textarea input', () => {
    render(<EngineCompareView />)
    
    expect(screen.getByPlaceholderText(/Enter text to analyze/i)).toBeInTheDocument()
  })

  it('should render compare button', () => {
    render(<EngineCompareView />)
    
    expect(screen.getByRole('button', { name: /Compare/i })).toBeInTheDocument()
  })

  it('should render engine name in header', () => {
    render(<EngineCompareView />)
    
    expect(screen.getByText('Compare Engines')).toBeInTheDocument()
  })

  it('should show empty state before analysis', () => {
    render(<EngineCompareView />)
    
    expect(screen.getByText(/Enter text above to compare/i)).toBeInTheDocument()
  })

  it('should disable button when textarea is empty', () => {
    render(<EngineCompareView />)
    
    const compareButton = screen.getByRole('button', { name: /Compare/i })
    expect(compareButton).toBeDisabled()
  })

  it('should enable button when textarea has text', async () => {
    const user = userEvent.setup()
    render(<EngineCompareView />)

    const input = screen.getByPlaceholderText(/Enter text to analyze/i)
    await user.type(input, 'some text')

    const compareButton = screen.getByRole('button', { name: /Compare/i })
    expect(compareButton).not.toBeDisabled()
  })

  it('should show loading state during analysis', async () => {
    const user = userEvent.setup()
    
    // Never resolve to keep loading state
    mockFetch.mockImplementation(() => new Promise(() => {}))

    render(<EngineCompareView />)

    const input = screen.getByPlaceholderText(/Enter text to analyze/i)
    await user.type(input, 'test')

    const compareButton = screen.getByRole('button', { name: /Compare/i })
    await user.click(compareButton)

    expect(screen.getByText(/Analyzing/i)).toBeInTheDocument()
  })
})
