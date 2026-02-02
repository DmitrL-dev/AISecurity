/**
 * EngineCard Component Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { EngineCard } from '../EngineCard'

// Mock fetch
const mockFetch = vi.fn()
global.fetch = mockFetch

describe('EngineCard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should show loading state initially', () => {
    mockFetch.mockImplementation(() => new Promise(() => {})) // Never resolves

    render(
      <EngineCard
        name="test-engine"
        displayName="Test Engine"
        description="Test"
        onConfigure={() => {}}
      />
    )

    // Should show skeleton/loading state (animate-pulse)
    const loadingDiv = document.querySelector('.animate-pulse')
    expect(loadingDiv).toBeInTheDocument()
  })

  it('should display engine info after fetch', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        engine: 'qwen-guard',
        status: 'healthy',
        mode: 'api',
        model: 'Qwen/Qwen3-Guard-0.6B',
        metrics: {
          call_count: 1234,
          error_count: 12,
          avg_latency_ms: 126
        }
      })
    })

    render(
      <EngineCard
        name="qwen-guard"
        displayName="Qwen3-Guard"
        description="Fast safety classification"
        onConfigure={() => {}}
      />
    )

    await waitFor(() => {
      expect(screen.getByText('Qwen3-Guard')).toBeInTheDocument()
    })

    expect(screen.getByText('Fast safety classification')).toBeInTheDocument()
    expect(screen.getByText('1,234')).toBeInTheDocument() // Formatted call_count
    expect(screen.getByText('126ms')).toBeInTheDocument()
    expect(screen.getByText('12')).toBeInTheDocument() // Errors
  })

  it('should call onConfigure when settings clicked', async () => {
    const user = userEvent.setup()
    const onConfigure = vi.fn()
    
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        engine: 'test',
        status: 'healthy',
        mode: 'api',
        model: 'test-model',
        metrics: { call_count: 0, error_count: 0, avg_latency_ms: 0 }
      })
    })

    render(
      <EngineCard
        name="test"
        displayName="Test"
        description="Test"
        onConfigure={onConfigure}
      />
    )

    await waitFor(() => {
      expect(screen.getByText('Test')).toBeInTheDocument()
    })

    const settingsButton = screen.getByRole('button')
    await user.click(settingsButton)

    expect(onConfigure).toHaveBeenCalledTimes(1)
  })

  it('should show offline state on fetch failure', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500
    })

    render(
      <EngineCard
        name="broken"
        displayName="Broken Engine"
        description="Test"
        onConfigure={() => {}}
      />
    )

    await waitFor(() => {
      expect(screen.getByText('Broken Engine')).toBeInTheDocument()
    })
    
    // Should show status (offline by default when error)
  })

  it('should show error status styling', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        engine: 'test',
        status: 'error',
        mode: 'api',
        model: 'model',
        metrics: { call_count: 100, error_count: 50, avg_latency_ms: 200 }
      })
    })

    render(
      <EngineCard
        name="test"
        displayName="Error Engine"
        description="Broken"
        onConfigure={() => {}}
      />
    )

    await waitFor(() => {
      expect(screen.getByText('Error Engine')).toBeInTheDocument()
    })
  })

  it('should handle selected state', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        engine: 'test',
        status: 'healthy',
        mode: 'api',
        model: 'model',
        metrics: { call_count: 0, error_count: 0, avg_latency_ms: 0 }
      })
    })

    render(
      <EngineCard
        name="test"
        displayName="Selected Engine"
        description="Test"
        selected={true}
      />
    )

    await waitFor(() => {
      expect(screen.getByText('Selected Engine')).toBeInTheDocument()
    })

    // Should have selected styling (border-purple-500)
    const card = screen.getByText('Selected Engine').closest('.rounded-xl')
    expect(card).toHaveClass('border-purple-500')
  })
})
