'use client'

import { useState } from 'react'
import { Shield, ExternalLink, ChevronDown, ChevronRight } from 'lucide-react'

interface MitreTechnique {
  id: string
  name: string
  tactic: string
  confidence: number
  description?: string
}

interface MitreAttackMapProps {
  techniques: MitreTechnique[]
  compact?: boolean
}

// MITRE ATT&CK Tactics in kill chain order
const TACTICS = [
  { id: 'reconnaissance', name: 'Recon', color: 'bg-slate-500' },
  { id: 'resource-development', name: 'Resource Dev', color: 'bg-slate-600' },
  { id: 'initial-access', name: 'Initial Access', color: 'bg-red-600' },
  { id: 'execution', name: 'Execution', color: 'bg-orange-600' },
  { id: 'persistence', name: 'Persistence', color: 'bg-amber-600' },
  { id: 'privilege-escalation', name: 'Priv Esc', color: 'bg-yellow-600' },
  { id: 'defense-evasion', name: 'Defense Evasion', color: 'bg-lime-600' },
  { id: 'credential-access', name: 'Cred Access', color: 'bg-green-600' },
  { id: 'discovery', name: 'Discovery', color: 'bg-emerald-600' },
  { id: 'lateral-movement', name: 'Lateral Move', color: 'bg-teal-600' },
  { id: 'collection', name: 'Collection', color: 'bg-cyan-600' },
  { id: 'command-and-control', name: 'C2', color: 'bg-blue-600' },
  { id: 'exfiltration', name: 'Exfiltration', color: 'bg-indigo-600' },
  { id: 'impact', name: 'Impact', color: 'bg-purple-600' },
]

function getTacticColor(tactic: string): string {
  const found = TACTICS.find(t => 
    t.id === tactic.toLowerCase() || 
    t.name.toLowerCase() === tactic.toLowerCase()
  )
  return found?.color || 'bg-gray-600'
}

function getConfidenceColor(confidence: number): string {
  if (confidence >= 0.8) return 'border-red-500 bg-red-500/20'
  if (confidence >= 0.6) return 'border-orange-500 bg-orange-500/20'
  if (confidence >= 0.4) return 'border-yellow-500 bg-yellow-500/20'
  return 'border-gray-500 bg-gray-500/20'
}

export function MitreAttackMap({ techniques, compact = false }: MitreAttackMapProps) {
  const [expanded, setExpanded] = useState<string | null>(null)
  const [showAll, setShowAll] = useState(false)

  if (!techniques || techniques.length === 0) {
    return (
      <div className="text-center py-6 text-gray-500">
        <Shield className="w-8 h-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No MITRE techniques detected</p>
      </div>
    )
  }

  // Group by tactic
  const byTactic = techniques.reduce((acc, tech) => {
    const tactic = tech.tactic || 'unknown'
    if (!acc[tactic]) acc[tactic] = []
    acc[tactic].push(tech)
    return acc
  }, {} as Record<string, MitreTechnique[]>)

  const displayTechniques = showAll ? techniques : techniques.slice(0, 6)

  if (compact) {
    // Compact view - just chips
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-xs text-gray-400 mb-2">
          <Shield className="w-3.5 h-3.5" />
          MITRE ATT&CK ({techniques.length})
        </div>
        <div className="flex flex-wrap gap-1.5">
          {displayTechniques.map((tech) => (
            <a
              key={tech.id}
              href={`https://attack.mitre.org/techniques/${tech.id.replace('.', '/')}`}
              target="_blank"
              rel="noopener noreferrer"
              className={`px-2 py-0.5 rounded text-xs font-mono border ${getConfidenceColor(tech.confidence)} hover:opacity-80 transition-opacity flex items-center gap-1`}
              title={`${tech.name} (${tech.tactic})`}
            >
              {tech.id}
              <ExternalLink className="w-2.5 h-2.5 opacity-50" />
            </a>
          ))}
          {!showAll && techniques.length > 6 && (
            <button
              onClick={() => setShowAll(true)}
              className="px-2 py-0.5 rounded text-xs bg-gray-700 hover:bg-gray-600 transition-colors"
            >
              +{techniques.length - 6} more
            </button>
          )}
        </div>
      </div>
    )
  }

  // Full view - grouped by tactic
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-medium">
          <Shield className="w-4 h-4 text-red-400" />
          MITRE ATT&CK Mapping
        </div>
        <span className="text-xs text-gray-500">
          {techniques.length} technique{techniques.length !== 1 ? 's' : ''} detected
        </span>
      </div>

      {/* Tactic timeline */}
      <div className="flex gap-1 overflow-x-auto pb-2">
        {TACTICS.map((tactic) => {
          const count = byTactic[tactic.id]?.length || byTactic[tactic.name.toLowerCase()]?.length || 0
          return (
            <div
              key={tactic.id}
              className={`flex-shrink-0 px-2 py-1 rounded text-[10px] font-medium ${
                count > 0 ? tactic.color + ' text-white' : 'bg-gray-800 text-gray-500'
              }`}
              title={`${tactic.name}: ${count} techniques`}
            >
              {count > 0 && <span className="mr-1">{count}</span>}
              {tactic.name}
            </div>
          )
        })}
      </div>

      {/* Techniques list */}
      <div className="space-y-2">
        {Object.entries(byTactic).map(([tactic, techs]) => (
          <div key={tactic} className="bg-gray-800/50 rounded-lg overflow-hidden">
            <button
              onClick={() => setExpanded(expanded === tactic ? null : tactic)}
              className="w-full flex items-center justify-between px-3 py-2 hover:bg-gray-700/50 transition-colors"
            >
              <div className="flex items-center gap-2">
                {expanded === tactic ? (
                  <ChevronDown className="w-4 h-4 text-gray-400" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-gray-400" />
                )}
                <span className={`px-2 py-0.5 rounded text-xs ${getTacticColor(tactic)}`}>
                  {tactic}
                </span>
                <span className="text-sm text-gray-300">{techs.length} techniques</span>
              </div>
            </button>
            
            {expanded === tactic && (
              <div className="px-3 pb-3 space-y-2">
                {techs.map((tech) => (
                  <a
                    key={tech.id}
                    href={`https://attack.mitre.org/techniques/${tech.id.replace('.', '/')}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block p-2 bg-gray-900/50 rounded border border-gray-700 hover:border-gray-600 transition-colors"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs text-purple-400">{tech.id}</span>
                        <span className="text-sm">{tech.name}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-16 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                          <div 
                            className={`h-full ${tech.confidence >= 0.8 ? 'bg-red-500' : tech.confidence >= 0.6 ? 'bg-orange-500' : 'bg-yellow-500'}`}
                            style={{ width: `${tech.confidence * 100}%` }}
                          />
                        </div>
                        <span className="text-xs text-gray-500">{Math.round(tech.confidence * 100)}%</span>
                        <ExternalLink className="w-3.5 h-3.5 text-gray-500" />
                      </div>
                    </div>
                    {tech.description && (
                      <p className="text-xs text-gray-500 mt-1 line-clamp-2">{tech.description}</p>
                    )}
                  </a>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

export default MitreAttackMap
