/**
 * MitreAttackMap Component Tests
 */

import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MitreAttackMap } from '../MitreAttackMap'

const mockTechniques = [
  { id: 'T1059.001', name: 'PowerShell', tactic: 'execution', confidence: 0.94 },
  { id: 'T1027', name: 'Obfuscated Files', tactic: 'defense-evasion', confidence: 0.78 },
  { id: 'T1003', name: 'OS Credential Dumping', tactic: 'credential-access', confidence: 0.65 },
]

describe('MitreAttackMap', () => {
  it('should render empty state when no techniques', () => {
    render(<MitreAttackMap techniques={[]} />)
    
    expect(screen.getByText('No MITRE techniques detected')).toBeInTheDocument()
  })

  it('should render technique count', () => {
    render(<MitreAttackMap techniques={mockTechniques} />)
    
    expect(screen.getByText('3 techniques detected')).toBeInTheDocument()
  })

  it('should render tactics in timeline', () => {
    render(<MitreAttackMap techniques={mockTechniques} />)
    
    // Check some key tactics are present
    expect(screen.getByText('Execution')).toBeInTheDocument()
    expect(screen.getByText('Defense Evasion')).toBeInTheDocument()
    expect(screen.getByText('Cred Access')).toBeInTheDocument()
  })

  it('should expand tactic group on click', async () => {
    const user = userEvent.setup()
    render(<MitreAttackMap techniques={mockTechniques} />)
    
    // Click on execution tactic group - find button containing 'execution'
    const executionButton = screen.getByText('execution').closest('button')
    expect(executionButton).toBeInTheDocument()
    
    if (executionButton) {
      await user.click(executionButton)
      
      // Should show the technique details
      expect(screen.getByText('T1059.001')).toBeInTheDocument()
      expect(screen.getByText('PowerShell')).toBeInTheDocument()
    }
  })

  it('should render compact mode with chips', () => {
    render(<MitreAttackMap techniques={mockTechniques} compact />)
    
    // In compact mode, should show technique IDs as links
    expect(screen.getByText('T1059.001')).toBeInTheDocument()
    expect(screen.getByText('T1027')).toBeInTheDocument()
    expect(screen.getByText('T1003')).toBeInTheDocument()
  })

  it('should show +N more button when many techniques in compact mode', () => {
    const manyTechniques = Array.from({ length: 10 }, (_, i) => ({
      id: `T100${i}`,
      name: `Technique ${i}`,
      tactic: 'execution',
      confidence: 0.5 + i * 0.05
    }))
    
    render(<MitreAttackMap techniques={manyTechniques} compact />)
    
    // Should show "+4 more" button (10 - 6 = 4)
    expect(screen.getByText('+4 more')).toBeInTheDocument()
  })

  it('should render external MITRE links in compact mode', () => {
    render(<MitreAttackMap techniques={mockTechniques} compact />)
    
    const links = screen.getAllByRole('link')
    expect(links.length).toBeGreaterThan(0)
    
    // Check first link points to MITRE
    const firstLink = links[0]
    expect(firstLink).toHaveAttribute('href', expect.stringContaining('attack.mitre.org'))
    expect(firstLink).toHaveAttribute('target', '_blank')
  })

  it('should render confidence percentage after expanding', async () => {
    const user = userEvent.setup()
    render(<MitreAttackMap techniques={mockTechniques} />)
    
    // Expand a group
    const tacticButton = screen.getByText('execution').closest('button')
    if (tacticButton) {
      await user.click(tacticButton)
      
      // Check confidence is shown (94%)
      expect(screen.getByText('94%')).toBeInTheDocument()
    }
  })

  it('should show MITRE ATT&CK header text', () => {
    render(<MitreAttackMap techniques={mockTechniques} />)
    
    expect(screen.getByText('MITRE ATT&CK Mapping')).toBeInTheDocument()
  })

  it('should group techniques by tactic', async () => {
    const user = userEvent.setup()
    render(<MitreAttackMap techniques={mockTechniques} />)
    
    // Should show 3 tactic groups
    expect(screen.getByText('execution')).toBeInTheDocument()
    expect(screen.getByText('defense-evasion')).toBeInTheDocument()
    expect(screen.getByText('credential-access')).toBeInTheDocument()
  })
})
