'use client'

import { useState } from 'react'
import { 
  Brain, 
  Power, 
  Activity, 
  Clock, 
  CheckCircle, 
  XCircle,
  Search,
  Play,
  Pause,
  Send,
  Loader2,
  AlertTriangle,
  ShieldCheck
} from 'lucide-react'
import { useAnalyze } from '@/lib/hooks'

interface Engine {
  name: string
  category: string
  description: string
  enabled: boolean
  health: 'healthy' | 'degraded' | 'error'
  lastRun?: string
  detections: number
}

// Mock data - will be replaced with real API
const mockEngines: Engine[] = [
  { name: 'injection', category: 'Core Detection', description: 'Prompt injection detection using ML classifiers', enabled: true, health: 'healthy', lastRun: '2s ago', detections: 1247 },
  { name: 'pii', category: 'Data Protection', description: 'Personal Identifiable Information detection', enabled: true, health: 'healthy', lastRun: '5s ago', detections: 892 },
  { name: 'rag_guard', category: 'RAG Security', description: 'RAG context poisoning and retrieval attacks', enabled: true, health: 'healthy', lastRun: '3s ago', detections: 456 },
  { name: 'tda_enhanced', category: 'Strange Math', description: 'Topological Data Analysis for anomaly detection', enabled: true, health: 'healthy', lastRun: '8s ago', detections: 234 },
  { name: 'behavioral', category: 'Core Detection', description: 'Behavioral pattern analysis for jailbreaks', enabled: true, health: 'healthy', lastRun: '1s ago', detections: 678 },
  { name: 'yara', category: 'Signature', description: 'YARA rule-based pattern matching', enabled: true, health: 'healthy', lastRun: '4s ago', detections: 123 },
  { name: 'mcp_a2a', category: 'Protocol', description: 'MCP and A2A protocol security', enabled: false, health: 'degraded', detections: 0 },
  { name: 'sheaf', category: 'Strange Math', description: 'Sheaf theory for semantic consistency', enabled: false, health: 'degraded', detections: 0 },
]

const healthConfig = {
  healthy: { icon: CheckCircle, color: 'text-green-400', bg: 'bg-green-500/20' },
  degraded: { icon: Clock, color: 'text-yellow-400', bg: 'bg-yellow-500/20' },
  error: { icon: XCircle, color: 'text-red-400', bg: 'bg-red-500/20' },
}

// Payload Testing Component
function PayloadTester() {
  const [payload, setPayload] = useState('')
  const { analyze, analyzing, result } = useAnalyze()
  const [testResult, setTestResult] = useState<any>(null)

  const handleTest = async () => {
    if (!payload.trim()) return
    try {
      const res = await analyze({ prompt: payload })
      setTestResult(res)
    } catch {
      setTestResult({ error: true, message: 'Analysis failed' })
    }
  }

  return (
    <div className="bg-[#1a1f2e] rounded-xl border border-[#374151] p-4">
      <h3 className="font-semibold text-lg mb-4 flex items-center gap-2">
        <Play className="w-5 h-5 text-purple-400" />
        Live Payload Testing
      </h3>
      
      <div className="space-y-4">
        <div>
          <label className="text-xs text-gray-400 mb-2 block">Enter payload to analyze</label>
          <textarea
            value={payload}
            onChange={(e) => setPayload(e.target.value)}
            placeholder="Enter a suspicious prompt or payload to test against BRAIN engines..."
            className="w-full h-32 px-3 py-2 bg-[#111827] rounded-lg border border-[#374151] focus:border-purple-500 focus:outline-none text-sm resize-none font-mono"
          />
        </div>
        
        <button
          onClick={handleTest}
          disabled={analyzing || !payload.trim()}
          className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-purple-500 hover:bg-purple-600 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors"
        >
          {analyzing ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <Send className="w-4 h-4" />
              Test Payload
            </>
          )}
        </button>
        
        {/* Results */}
        {testResult && (
          <div className={`p-4 rounded-lg border ${
            testResult.error 
              ? 'bg-red-500/10 border-red-500/30' 
              : testResult.is_safe 
                ? 'bg-green-500/10 border-green-500/30' 
                : 'bg-red-500/10 border-red-500/30'
          }`}>
            <div className="flex items-start gap-3">
              {testResult.error ? (
                <XCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
              ) : testResult.is_safe ? (
                <ShieldCheck className="w-5 h-5 text-green-400 flex-shrink-0" />
              ) : (
                <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0" />
              )}
              <div className="flex-1">
                <p className="font-medium">
                  {testResult.error 
                    ? 'Analysis Failed' 
                    : testResult.is_safe 
                      ? 'Payload Safe' 
                      : 'Threat Detected!'
                  }
                </p>
                {!testResult.error && (
                  <>
                    <p className="text-sm text-gray-400 mt-1">
                      Risk Score: <span className={testResult.risk_score > 0.5 ? 'text-red-400' : 'text-green-400'}>
                        {(testResult.risk_score * 100).toFixed(1)}%
                      </span>
                    </p>
                    {testResult.detections?.length > 0 && (
                      <div className="mt-2 space-y-1">
                        {testResult.detections.map((d: any, i: number) => (
                          <p key={i} className="text-xs text-red-400">
                            • {d.threat_type} ({d.engine})
                          </p>
                        ))}
                      </div>
                    )}
                    <p className="text-xs text-gray-500 mt-2">
                      Processed in {testResult.latency_ms?.toFixed(0) || testResult.processing_time_ms}ms
                      {testResult._mock && (
                        <span className="ml-2 px-1.5 py-0.5 bg-yellow-500/20 text-yellow-400 rounded text-[10px]">
                          MOCK
                        </span>
                      )}
                      {!testResult._mock && !testResult.error && (
                        <span className="ml-2 px-1.5 py-0.5 bg-green-500/20 text-green-400 rounded text-[10px]">
                          BRAIN API
                        </span>
                      )}
                    </p>
                  </>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default function BrainPage() {
  const [engines, setEngines] = useState(mockEngines)
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('all')

  const categories = ['all', ...new Set(mockEngines.map(e => e.category))]

  const filteredEngines = engines.filter(e => {
    if (category !== 'all' && e.category !== category) return false
    if (search && !e.name.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  const toggleEngine = (name: string) => {
    setEngines(engines.map(e => 
      e.name === name ? { ...e, enabled: !e.enabled } : e
    ))
  }

  const stats = {
    total: engines.length,
    enabled: engines.filter(e => e.enabled).length,
    healthy: engines.filter(e => e.health === 'healthy').length,
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Brain className="w-7 h-7 text-purple-400" />
            BRAIN Engines
          </h1>
          <p className="text-gray-400 text-sm">Manage and monitor detection engines</p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-[#1a1f2e] rounded-xl border border-[#374151] p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-purple-500/20">
              <Brain className="w-5 h-5 text-purple-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats.total}</p>
              <p className="text-sm text-gray-400">Total Engines</p>
            </div>
          </div>
        </div>
        <div className="bg-[#1a1f2e] rounded-xl border border-[#374151] p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-cyan-500/20">
              <Power className="w-5 h-5 text-cyan-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats.enabled}/{stats.total}</p>
              <p className="text-sm text-gray-400">Enabled</p>
            </div>
          </div>
        </div>
        <div className="bg-[#1a1f2e] rounded-xl border border-[#374151] p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-green-500/20">
              <Activity className="w-5 h-5 text-green-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats.healthy}</p>
              <p className="text-sm text-gray-400">Healthy</p>
            </div>
          </div>
        </div>
      </div>

      {/* Main Grid: Engines + Payload Tester */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Engines List (2 cols) */}
        <div className="lg:col-span-2 space-y-4">
          {/* Filters */}
          <div className="flex gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search engines..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-[#1a1f2e] rounded-lg border border-[#374151] focus:border-purple-500 focus:outline-none"
              />
            </div>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="px-4 py-2 bg-[#1a1f2e] rounded-lg border border-[#374151] focus:border-purple-500 focus:outline-none"
            >
              {categories.map(c => (
                <option key={c} value={c}>{c === 'all' ? 'All Categories' : c}</option>
              ))}
            </select>
          </div>

          {/* Engines Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredEngines.map((engine) => {
              const HealthIcon = healthConfig[engine.health].icon
              return (
                <div 
                  key={engine.name}
                  className={`
                    bg-[#1a1f2e] rounded-xl border p-4 transition-all duration-200
                    ${engine.enabled ? 'border-[#374151] hover:border-purple-500/50' : 'border-[#374151]/50 opacity-60'}
                  `}
                >
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <h3 className="font-semibold text-lg">{engine.name}</h3>
                      <span className="text-xs text-purple-400">{engine.category}</span>
                    </div>
                    <button
                      onClick={() => toggleEngine(engine.name)}
                      className={`
                        p-2 rounded-lg transition-colors
                        ${engine.enabled ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'}
                      `}
                    >
                      {engine.enabled ? <Power className="w-4 h-4" /> : <Pause className="w-4 h-4" />}
                    </button>
                  </div>
                  
                  <p className="text-sm text-gray-400 mb-4">{engine.description}</p>
                  
                  <div className="flex items-center justify-between text-sm">
                    <span className={`flex items-center gap-1 ${healthConfig[engine.health].color}`}>
                      <HealthIcon className="w-4 h-4" />
                      {engine.health}
                    </span>
                    {engine.enabled && (
                      <>
                        <span className="text-gray-400">Last: {engine.lastRun}</span>
                        <span className="text-cyan-400">{engine.detections} detections</span>
                      </>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {/* Payload Tester (1 col) */}
        <div className="lg:col-span-1">
          <PayloadTester />
        </div>
      </div>
    </div>
  )
}
