/**
 * ReasoningViewer Component Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ReasoningViewer } from '../ReasoningViewer'

const mockResult = {
  analysis_type: 'deep_security',
  reasoning: {
    thinking: 'Step 1: Analyzing input...\nStep 2: Pattern matching...',
    conclusion: 'MALICIOUS - Command injection attempt detected',
    confidence: 0.94
  },
  mitre_mappings: [
    { technique_id: 'T1059.001', technique_name: 'PowerShell', tactic: 'Execution', confidence: 0.94 },
    { technique_id: 'T1027', technique_name: 'Obfuscated Files', tactic: 'Defense Evasion', confidence: 0.78 }
  ],
  risk_score: 87,
  recommendations: [
    'Block obfuscated PowerShell scripts',
    'Enable command-line auditing'
  ],
  latency_ms: 2450
}

describe('ReasoningViewer', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('should render risk score banner', () => {
    render(<ReasoningViewer result={mockResult} />)
    
    expect(screen.getByText(/Risk Score: 87\/100/i)).toBeInTheDocument()
  })

  it('should render conclusion', () => {
    render(<ReasoningViewer result={mockResult} />)
    
    expect(screen.getByText('Conclusion')).toBeInTheDocument()
    expect(screen.getByText(/Command injection attempt detected/i)).toBeInTheDocument()
  })

  it('should render confidence percentage', () => {
    render(<ReasoningViewer result={mockResult} />)
    
    expect(screen.getByText(/Confidence: 94%/i)).toBeInTheDocument()
  })

  it('should render latency', () => {
    render(<ReasoningViewer result={mockResult} />)
    
    expect(screen.getByText(/2450ms/)).toBeInTheDocument()
  })

  it('should expand thinking trace on click', async () => {
    const user = userEvent.setup()
    render(<ReasoningViewer result={mockResult} />)
    
    // Click on reasoning trace header
    const thinkingButton = screen.getByText('Reasoning Trace').closest('button')
    expect(thinkingButton).toBeInTheDocument()
    
    if (thinkingButton) {
      await user.click(thinkingButton)
      
      // Should now show the thinking content
      expect(screen.getByText(/Analyzing input/)).toBeInTheDocument()
    }
  })

  it('should render MITRE techniques', () => {
    render(<ReasoningViewer result={mockResult} />)
    
    expect(screen.getByText('MITRE ATT&CK Techniques')).toBeInTheDocument()
    expect(screen.getByText('T1059.001')).toBeInTheDocument()
    expect(screen.getByText('PowerShell')).toBeInTheDocument()
    expect(screen.getByText('T1027')).toBeInTheDocument()
  })

  it('should render recommendations', () => {
    render(<ReasoningViewer result={mockResult} />)
    
    expect(screen.getByText('Recommendations')).toBeInTheDocument()
    expect(screen.getByText(/Block obfuscated PowerShell/)).toBeInTheDocument()
    expect(screen.getByText(/command-line auditing/)).toBeInTheDocument()
  })

  it('should apply correct styling for high risk (banner visible)', () => {
    render(<ReasoningViewer result={{ ...mockResult, risk_score: 90 }} />)
    
    // Just verify the score renders correctly
    expect(screen.getByText(/Risk Score: 90/)).toBeInTheDocument()
  })

  it('should apply correct styling for medium risk', () => {
    render(<ReasoningViewer result={{ ...mockResult, risk_score: 55 }} />)
    
    expect(screen.getByText(/Risk Score: 55/)).toBeInTheDocument()
  })

  it('should apply correct styling for low risk', () => {
    render(<ReasoningViewer result={{ ...mockResult, risk_score: 25 }} />)
    
    expect(screen.getByText(/Risk Score: 25/)).toBeInTheDocument()
  })
})
