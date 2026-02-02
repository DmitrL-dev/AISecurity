/**
 * EngineStatsPanel Component Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { EngineStatsPanel } from '../EngineStatsPanel'

const mockFetch = vi.fn()
global.fetch = mockFetch

describe('EngineStatsPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should show loading state initially', () => {
    mockFetch.mockImplementation(() => new Promise(() => {}))
    
    render(<EngineStatsPanel engineName="test-engine" />)
    
    // Should show skeleton/loading elements
    const loadingElements = document.querySelectorAll('.animate-pulse')
    expect(loadingElements.length).toBeGreaterThan(0)
  })

  it('should display stats after successful fetch', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        calls: 5000,
        latency_ms: 150,
        errors: 25,
        status: 'healthy'
      })
    })

    render(<EngineStatsPanel engineName="qwen-guard" />)

    await waitFor(() => {
      expect(screen.getByText(/5,000/)).toBeInTheDocument()
    })
  })

  it('should show error state on fetch failure', async () => {
    mockFetch.mockRejectedValueOnce(new Error('API Error'))

    render(<EngineStatsPanel engineName="broken-engine" />)

    await waitFor(() => {
      expect(screen.getByText(/Failed to load metrics/i)).toBeInTheDocument()
    })
  })

  it('should display latency percentiles', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        calls: 1000,
        latency_ms: 100,
        errors: 5,
        status: 'healthy'
      })
    })

    render(<EngineStatsPanel engineName="test-engine" />)

    await waitFor(() => {
      expect(screen.getByText('P50 (Median)')).toBeInTheDocument()
      expect(screen.getByText('P95')).toBeInTheDocument()
      expect(screen.getByText('P99')).toBeInTheDocument()
    })
  })

  it('should calculate success rate correctly', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        calls: 100,
        latency_ms: 50,
        errors: 5, // 5% error rate = 95% success
        status: 'healthy'
      })
    })

    render(<EngineStatsPanel engineName="test" />)

    await waitFor(() => {
      expect(screen.getByText(/95\.0%/)).toBeInTheDocument()
    })
  })

  it('should show green color for high success rate', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        calls: 1000,
        latency_ms: 50,
        errors: 1, // 99.9% success
        status: 'healthy'
      })
    })

    render(<EngineStatsPanel engineName="test" />)

    await waitFor(() => {
      const successRateCard = screen.getByText('Success Rate').closest('div')
      expect(successRateCard).toBeInTheDocument()
    })
  })

  it('should render 24h charts section', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({
        calls: 500,
        latency_ms: 75,
        errors: 3,
        status: 'healthy'
      })
    })

    render(<EngineStatsPanel engineName="test" />)

    await waitFor(() => {
      expect(screen.getByText('Calls (24h)')).toBeInTheDocument()
      expect(screen.getByText('Latency (24h)')).toBeInTheDocument()
      expect(screen.getByText('Errors (24h)')).toBeInTheDocument()
    })
  })

  it('should refresh data at specified interval', async () => {
    vi.useFakeTimers()
    
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({
        calls: 100,
        latency_ms: 50,
        errors: 1,
        status: 'healthy'
      })
    })

    render(<EngineStatsPanel engineName="test" refreshInterval={5000} />)

    // Initial fetch
    expect(mockFetch).toHaveBeenCalledTimes(1)

    // Advance time
    vi.advanceTimersByTime(5000)
    
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(2)
    })

    vi.useRealTimers()
  })
})
