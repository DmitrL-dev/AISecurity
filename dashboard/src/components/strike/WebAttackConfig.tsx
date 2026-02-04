'use client'

import { useState, useEffect } from 'react'
import { 
  Bug, 
  Database, 
  FileCode, 
  Globe, 
  Terminal, 
  Code, 
  FileJson,
  Loader2,
  AlertTriangle
} from 'lucide-react'

interface WebVector {
  id: string
  name: string
  count: number
  severity: 'critical' | 'high' | 'medium' | 'low'
  category: string
}

interface WebAttackConfigProps {
  selectedVectors: string[]
  onVectorsChange: (vectors: string[]) => void
  targetParam: string
  onTargetParamChange: (param: string) => void
}

const VECTOR_ICONS: Record<string, React.ReactNode> = {
  sqli: <Database className="w-4 h-4" />,
  xss: <Code className="w-4 h-4" />,
  lfi: <FileCode className="w-4 h-4" />,
  ssrf: <Globe className="w-4 h-4" />,
  cmdi: <Terminal className="w-4 h-4" />,
  ssti: <Code className="w-4 h-4" />,
  xxe: <FileJson className="w-4 h-4" />,
  nosql: <Database className="w-4 h-4" />,
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: 'text-red-400 bg-red-500/20',
  high: 'text-orange-400 bg-orange-500/20',
  medium: 'text-yellow-400 bg-yellow-500/20',
  low: 'text-green-400 bg-green-500/20',
}

export default function WebAttackConfig({
  selectedVectors,
  onVectorsChange,
  targetParam,
  onTargetParamChange,
}: WebAttackConfigProps) {
  const [vectors, setVectors] = useState<WebVector[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [totalPayloads, setTotalPayloads] = useState(0)

  useEffect(() => {
    fetchVectors()
  }, [])

  const fetchVectors = async () => {
    try {
      setLoading(true)
      const res = await fetch('/api/strike/vectors/web')
      if (!res.ok) throw new Error('Failed to fetch vectors')
      const data = await res.json()
      setVectors(data.vectors || [])
      setTotalPayloads(data.total_payloads || 0)
      setError(null)
    } catch (_err) {
      setError('Failed to load web vectors')
      // Fallback vectors
      setVectors([
        { id: 'sqli', name: 'SQL Injection', count: 150, severity: 'critical', category: 'injection' },
        { id: 'xss', name: 'Cross-Site Scripting', count: 200, severity: 'high', category: 'injection' },
        { id: 'lfi', name: 'Local File Inclusion', count: 100, severity: 'high', category: 'file' },
        { id: 'ssrf', name: 'SSRF', count: 80, severity: 'high', category: 'file' },
        { id: 'cmdi', name: 'Command Injection', count: 60, severity: 'critical', category: 'injection' },
        { id: 'ssti', name: 'Template Injection', count: 50, severity: 'critical', category: 'injection' },
        { id: 'xxe', name: 'XXE', count: 40, severity: 'high', category: 'injection' },
        { id: 'nosql', name: 'NoSQL Injection', count: 30, severity: 'high', category: 'injection' },
      ])
      setTotalPayloads(800)
    } finally {
      setLoading(false)
    }
  }

  const toggleVector = (id: string) => {
    if (selectedVectors.includes(id)) {
      onVectorsChange(selectedVectors.filter(v => v !== id))
    } else {
      onVectorsChange([...selectedVectors, id])
    }
  }

  const selectAll = () => {
    onVectorsChange(vectors.map(v => v.id))
  }

  const clearAll = () => {
    onVectorsChange([])
  }

  const selectedCount = vectors
    .filter(v => selectedVectors.includes(v.id))
    .reduce((sum, v) => sum + v.count, 0)

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {error && (
        <div className="flex items-center gap-2 text-xs text-yellow-400 bg-yellow-500/10 p-2 rounded">
          <AlertTriangle className="w-4 h-4" />
          {error}
        </div>
      )}

      {/* Stats */}
      <div className="flex items-center justify-between text-xs text-gray-400">
        <span>
          <Bug className="w-3 h-3 inline mr-1" />
          {selectedCount.toLocaleString()} payloads selected
        </span>
        <span>{totalPayloads.toLocaleString()} total available</span>
      </div>

      {/* Quick Actions */}
      <div className="flex gap-2">
        <button
          type="button"
          onClick={selectAll}
          className="px-3 py-1 text-xs bg-purple-500/20 text-purple-400 rounded hover:bg-purple-500/30 transition-colors"
        >
          Select All
        </button>
        <button
          type="button"
          onClick={clearAll}
          className="px-3 py-1 text-xs bg-gray-500/20 text-gray-400 rounded hover:bg-gray-500/30 transition-colors"
        >
          Clear All
        </button>
      </div>

      {/* Vector Grid */}
      <div className="grid grid-cols-2 gap-2">
        {vectors.map(vector => (
          <button
            key={vector.id}
            type="button"
            onClick={() => toggleVector(vector.id)}
            className={`
              p-3 rounded-lg border text-left transition-all
              ${selectedVectors.includes(vector.id)
                ? 'border-purple-500 bg-purple-500/20'
                : 'border-[#374151] bg-[#0d1117] hover:border-[#4a5568]'
              }
            `}
          >
            <div className="flex items-center gap-2 mb-1">
              <span className={selectedVectors.includes(vector.id) ? 'text-purple-400' : 'text-gray-400'}>
                {VECTOR_ICONS[vector.id] || <Bug className="w-4 h-4" />}
              </span>
              <span className="text-sm font-medium">{vector.name}</span>
            </div>
            <div className="flex items-center gap-2">
              <span className={`text-xs px-1.5 py-0.5 rounded ${SEVERITY_COLORS[vector.severity]}`}>
                {vector.severity}
              </span>
              <span className="text-xs text-gray-500">{vector.count} payloads</span>
            </div>
          </button>
        ))}
      </div>

      {/* Target Parameter */}
      <div>
        <label className="block text-sm text-gray-400 mb-1">
          Target Parameter
          <span className="text-gray-600 ml-1">(e.g., id, q, search, user)</span>
        </label>
        <input
          type="text"
          value={targetParam}
          onChange={(e) => onTargetParamChange(e.target.value)}
          placeholder="id"
          className="w-full px-3 py-2 bg-[#0d1117] border border-[#374151] rounded-lg focus:border-purple-500 focus:outline-none text-sm"
        />
      </div>
    </div>
  )
}
