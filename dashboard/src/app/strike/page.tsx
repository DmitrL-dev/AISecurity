'use client'

import { useState, useEffect, useCallback } from 'react'
import { 
  Crosshair, 
  Play, 
  Pause,
  Square,
  RefreshCw,
  Search,
  AlertTriangle,
  Zap,
  Loader2,
  CheckCircle,
  X,
  Target,
  Activity,
  Wifi,
  WifiOff,
  ChevronDown,
  ChevronUp,
  Bug,
  FileText,
  Settings
} from 'lucide-react'
import WebAttackConfig from '@/components/strike/WebAttackConfig'
import { Brain, Globe, Zap as ZapIcon } from 'lucide-react'

// Types
interface AttackVector {
  name: string
  count: number
  severity: 'critical' | 'high' | 'medium' | 'low'
}

interface Attack {
  id: string
  state: string
  target: string
  iteration: number
  time_remaining: number
  successful_attacks: number
  total_attempts: number
  started_at: string | null
  current_payload?: string
  current_category?: string
  last_error?: string
  category?: string
}

interface StrikeHealth {
  status: string
  timestamp: string
  active_attacks: number
}

interface Finding {
  id: string
  payload: string
  response: string
  category: string
  severity: string
  timestamp: string
}

const severityConfig = {
  critical: 'bg-red-500/20 text-red-400 border-red-500/30',
  high: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
  medium: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  low: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
}

const stateConfig = {
  running: { bg: 'bg-orange-500/20', text: 'text-orange-400', border: 'border-orange-500/30' },
  paused: { bg: 'bg-yellow-500/20', text: 'text-yellow-400', border: 'border-yellow-500/30' },
  completed: { bg: 'bg-green-500/20', text: 'text-green-400', border: 'border-green-500/30' },
  stopped: { bg: 'bg-gray-500/20', text: 'text-gray-400', border: 'border-gray-500/30' },
  failed: { bg: 'bg-red-500/20', text: 'text-red-400', border: 'border-red-500/30' },
}

// Campaign Card Component
function CampaignCard({ 
  attack, 
  onStop, 
  onPause, 
  onResume,
  expanded,
  onToggle 
}: { 
  attack: Attack
  onStop: () => void
  onPause: () => void
  onResume: () => void
  expanded: boolean
  onToggle: () => void
}) {
  const [findings, setFindings] = useState<Finding[]>([])
  const [loadingFindings, setLoadingFindings] = useState(false)
  
  const state = stateConfig[attack.state as keyof typeof stateConfig] || stateConfig.stopped
  const isRunning = attack.state === 'running'
  const isPaused = attack.state === 'paused'
  const canControl = isRunning || isPaused

  // Load findings when expanded
  useEffect(() => {
    if (expanded && findings.length === 0) {
      setLoadingFindings(true)
      fetch(`/api/strike/attacks/${attack.id}/findings`)
        .then(res => res.json())
        .then(data => setFindings(data.findings || []))
        .catch(() => {})
        .finally(() => setLoadingFindings(false))
    }
  }, [expanded, attack.id, findings.length])

  const progress = attack.total_attempts > 0 
    ? Math.min((attack.iteration / Math.max(attack.total_attempts, 100)) * 100, 100) 
    : 0

  return (
    <div className={`rounded-xl border ${state.border} ${state.bg} overflow-hidden`}>
      {/* Header - Clickable */}
      <div 
        className="p-4 cursor-pointer hover:bg-white/5 transition-colors"
        onClick={onToggle}
      >
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs text-gray-500 font-mono">{attack.id}</span>
              <span className={`px-2 py-0.5 rounded text-xs font-medium ${state.bg} ${state.text}`}>
                {attack.state.toUpperCase()}
              </span>
              {attack.current_category && (
                <span className="px-2 py-0.5 rounded text-xs bg-purple-500/20 text-purple-400">
                  {attack.current_category}
                </span>
              )}
              {attack.time_remaining > 0 && (
                <span className="text-xs text-gray-500">
                  ⏱️ {attack.time_remaining}m remaining
                </span>
              )}
            </div>
            <p className="font-medium text-sm truncate max-w-md">{attack.target}</p>
          </div>
          
          {/* Controls - always visible for running/paused */}
          <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
            {canControl && (
              <>
                {isRunning ? (
                  <button
                    onClick={onPause}
                    className="p-2 rounded-lg bg-yellow-500/20 hover:bg-yellow-500/30 text-yellow-400 transition-colors"
                    title="Pause"
                  >
                    <Pause className="w-4 h-4" />
                  </button>
                ) : (
                  <button
                    onClick={onResume}
                    className="p-2 rounded-lg bg-green-500/20 hover:bg-green-500/30 text-green-400 transition-colors"
                    title="Resume"
                  >
                    <Play className="w-4 h-4" />
                  </button>
                )}
                <button
                  onClick={onStop}
                  className="p-2 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-red-400 transition-colors"
                  title="Stop"
                >
                  <Square className="w-4 h-4" />
                </button>
              </>
            )}
            <button
              onClick={onToggle}
              className="p-2 rounded-lg hover:bg-white/10 transition-colors"
            >
              {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
          </div>
        </div>
        
        {/* Progress Bar */}
        <div className="mt-3">
          <div className="flex justify-between text-xs text-gray-400 mb-1">
            <span>Progress: {attack.iteration} iterations</span>
            <span>
              {attack.successful_attacks > 0 ? (
                <span className="text-red-400">{attack.successful_attacks} bypasses found!</span>
              ) : (
                <span className="text-green-400">0 bypasses</span>
              )}
            </span>
          </div>
          <div className="h-2 bg-[#374151] rounded-full overflow-hidden">
            <div 
              className={`h-full transition-all duration-500 ${
                attack.successful_attacks > 0 ? 'bg-red-500' : 'bg-green-500'
              }`}
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* Last Error */}
        {attack.last_error && (
          <div className="mt-2 flex items-center gap-2 text-xs">
            <AlertTriangle className="w-3 h-3 text-red-400" />
            <span className="text-gray-400">Error: </span>
            <span className="text-red-400 truncate max-w-sm">{attack.last_error}</span>
          </div>
        )}
      </div>
      
      {/* Expanded Section */}
      {expanded && (
        <div className="border-t border-[#374151] p-4 bg-[#111827]/50">
          {/* Current Payload */}
          {attack.current_payload && (
            <div className="mb-4">
              <div className="flex items-center gap-2 text-xs text-gray-400 mb-1">
                <Bug className="w-3 h-3" />
                Current Payload
              </div>
              <div className="p-2 bg-[#1a1f2e] rounded text-xs font-mono text-gray-300 max-h-20 overflow-auto">
                {attack.current_payload}
              </div>
            </div>
          )}
          
          {/* Findings */}
          <div>
            <div className="flex items-center gap-2 text-xs text-gray-400 mb-2">
              <FileText className="w-3 h-3" />
              Findings ({findings.length})
            </div>
            {loadingFindings ? (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="w-4 h-4 animate-spin text-gray-400" />
              </div>
            ) : findings.length === 0 ? (
              <div className="text-xs text-gray-500 text-center py-4">
                No findings yet
              </div>
            ) : (
              <div className="space-y-2 max-h-40 overflow-auto">
                {findings.map((f, idx) => (
                  <div key={idx} className="p-2 bg-[#1a1f2e] rounded text-xs">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`px-1.5 py-0.5 rounded ${severityConfig[f.severity as keyof typeof severityConfig] || severityConfig.medium}`}>
                        {f.severity}
                      </span>
                      <span className="text-gray-400">{f.category}</span>
                    </div>
                    <div className="font-mono text-gray-300 truncate">{f.payload}</div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// New Attack Modal
function NewAttackModal({ 
  isOpen, 
  onClose, 
  onStart,
  loading 
}: { 
  isOpen: boolean
  onClose: () => void
  onStart: (config: { 
    target: string
    duration: number
    targetType: string
    attackMode: string
    webVectors: string[]
    targetParam: string
  }) => void
  loading: boolean
}) {
  const [target, setTarget] = useState('')
  const [duration, setDuration] = useState(5)
  const [targetType, setTargetType] = useState('custom')
  const [attackMode, setAttackMode] = useState<'llm' | 'web' | 'hybrid'>('llm')
  const [webVectors, setWebVectors] = useState<string[]>(['sqli', 'xss'])
  const [targetParam, setTargetParam] = useState('')

  if (!isOpen) return null

  return (
    <>
      <div className="fixed inset-0 bg-black/50 z-40" onClick={onClose} />
      <div className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[550px] max-w-[90vw] bg-[#111827] border border-[#374151] rounded-xl z-50 overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b border-[#374151]">
          <h2 className="font-semibold text-lg flex items-center gap-2">
            <Target className="w-5 h-5 text-red-400" />
            New Attack Campaign
          </h2>
          <button onClick={onClose} className="p-2 hover:bg-white/10 rounded-lg">
            <X className="w-4 h-4" />
          </button>
        </div>
        
        <div className="p-4 space-y-4 max-h-[60vh] overflow-y-auto">
          {/* Attack Mode */}
          <div>
            <label className="block text-sm text-gray-400 mb-2">Attack Mode</label>
            <div className="grid grid-cols-3 gap-2">
              {[
                { id: 'llm' as const, label: 'LLM/AI', icon: Brain, color: 'purple' },
                { id: 'web' as const, label: 'Web Attack', icon: Globe, color: 'red' },
                { id: 'hybrid' as const, label: 'Hybrid', icon: ZapIcon, color: 'yellow' },
              ].map(m => (
                <button
                  key={m.id}
                  onClick={() => setAttackMode(m.id)}
                  className={`p-3 rounded-lg border transition-all flex flex-col items-center gap-1 ${
                    attackMode === m.id 
                      ? `border-${m.color}-500 bg-${m.color}-500/10` 
                      : 'border-[#374151] hover:border-gray-500'
                  }`}
                >
                  <m.icon className={`w-5 h-5 ${attackMode === m.id ? `text-${m.color}-400` : 'text-gray-400'}`} />
                  <span className="text-xs">{m.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Web Attack Config (shown when Web or Hybrid mode) */}
          {(attackMode === 'web' || attackMode === 'hybrid') && (
            <div className="p-4 rounded-lg bg-red-500/5 border border-red-500/20">
              <h3 className="text-sm font-medium text-red-400 mb-3">Web Attack Vectors</h3>
              <WebAttackConfig
                selectedVectors={webVectors}
                onVectorsChange={setWebVectors}
                targetParam={targetParam}
                onTargetParamChange={setTargetParam}
              />
            </div>
          )}

          {/* Target Type */}
          <div>
            <label className="block text-sm text-gray-400 mb-2">Target Type</label>
            <div className="grid grid-cols-3 gap-2">
              {[
                { id: 'custom', label: 'Custom API', icon: Settings },
                { id: 'openai', label: 'OpenAI-compatible', icon: Zap },
                { id: 'web', label: 'Web Interface', icon: Target },
              ].map(t => (
                <button
                  key={t.id}
                  onClick={() => setTargetType(t.id)}
                  className={`p-3 rounded-lg border transition-all flex flex-col items-center gap-1 ${
                    targetType === t.id 
                      ? 'border-red-500 bg-red-500/10' 
                      : 'border-[#374151] hover:border-gray-500'
                  }`}
                >
                  <t.icon className={`w-5 h-5 ${targetType === t.id ? 'text-red-400' : 'text-gray-400'}`} />
                  <span className="text-xs">{t.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Target URL */}
          <div>
            <label className="block text-sm text-gray-400 mb-2">Target URL</label>
            <input
              type="text"
              value={target}
              onChange={(e) => setTarget(e.target.value)}
              placeholder={
                targetType === 'openai' 
                  ? 'https://api.openai.com/v1/chat/completions'
                  : targetType === 'web'
                    ? 'https://chat.example.com/'
                    : 'https://api.target.com/v1/chat'
              }
              className="w-full px-4 py-2 bg-[#1a1f2e] rounded-lg border border-[#374151] focus:border-red-500 focus:outline-none"
            />
          </div>
          
          {/* Duration */}
          <div>
            <label className="block text-sm text-gray-400 mb-2">Duration</label>
            <select
              value={duration}
              onChange={(e) => setDuration(Number(e.target.value))}
              className="w-full px-4 py-2 bg-[#1a1f2e] rounded-lg border border-[#374151] focus:border-red-500 focus:outline-none"
            >
              <option value={1}>1 minute (Quick Test)</option>
              <option value={5}>5 minutes (Standard)</option>
              <option value={15}>15 minutes (Deep Scan)</option>
              <option value={30}>30 minutes (Full Audit)</option>
              <option value={60}>1 hour (Marathon)</option>
            </select>
          </div>
        </div>
        
        <div className="p-4 border-t border-[#374151] flex justify-end gap-3">
          <button 
            onClick={onClose}
            className="px-4 py-2 border border-[#374151] rounded-lg hover:border-white/30 transition-colors"
          >
            Cancel
          </button>
          <button 
            onClick={() => onStart({ target, duration, targetType, attackMode, webVectors, targetParam })}
            disabled={!target || loading}
            className="flex items-center gap-2 px-4 py-2 bg-red-500 hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
            Start Attack
          </button>
        </div>
      </div>
    </>
  )
}

export default function StrikePage() {
  const [search, setSearch] = useState('')
  const [health, setHealth] = useState<StrikeHealth | null>(null)
  const [attacks, setAttacks] = useState<Attack[]>([])
  const [vectors, setVectors] = useState<Record<string, number>>({})
  const [payloads, setPayloads] = useState<{
    llm_vectors: number
    jailbreaks: number
    web_payloads: number
    total: number
  }>({ llm_vectors: 0, jailbreaks: 0, web_payloads: 0, total: 0 })
  const [loading, setLoading] = useState(true)
  const [newAttackOpen, setNewAttackOpen] = useState(false)
  const [startingAttack, setStartingAttack] = useState(false)
  const [expandedAttack, setExpandedAttack] = useState<string | null>(null)

  // Fetch Strike health & data
  const fetchData = useCallback(async () => {
    try {
      const [healthRes, attacksRes, vectorsRes, rootRes] = await Promise.all([
        fetch('/api/strike/health'),
        fetch('/api/strike/attacks'),
        fetch('/api/strike/vectors'),
        fetch('/api/strike')
      ])
      
      if (healthRes.ok) setHealth(await healthRes.json())
      if (attacksRes.ok) setAttacks(await attacksRes.json())
      if (vectorsRes.ok) setVectors(await vectorsRes.json())
      if (rootRes.ok) {
        const data = await rootRes.json()
        if (data.payloads) setPayloads(data.payloads)
      }
    } catch (error) {
      console.error('Failed to fetch Strike data:', error)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 3000)
    return () => clearInterval(interval)
  }, [fetchData])

  // Attack controls
  const stopAttack = async (id: string) => {
    try {
      await fetch(`/api/strike/attacks/${id}/stop`, { method: 'POST' })
      fetchData()
    } catch (error) {
      console.error('Failed to stop attack:', error)
    }
  }

  const pauseAttack = async (id: string) => {
    try {
      await fetch(`/api/strike/attacks/${id}/pause`, { method: 'POST' })
      fetchData()
    } catch (error) {
      console.error('Failed to pause attack:', error)
    }
  }

  const resumeAttack = async (id: string) => {
    try {
      await fetch(`/api/strike/attacks/${id}/resume`, { method: 'POST' })
      fetchData()
    } catch (error) {
      console.error('Failed to resume attack:', error)
    }
  }

  // Start new attack
  const startAttack = async (config: { 
    target: string
    duration: number
    targetType: string
    attackMode: string
    webVectors: string[]
    targetParam: string
  }) => {
    setStartingAttack(true)
    try {
      const res = await fetch('/api/strike/attacks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          target: config.target, 
          duration: config.duration, 
          stealth: true,
          target_type: config.targetType,
          attack_mode: config.attackMode,
          web_vectors: config.webVectors,
          target_param: config.targetParam
        })
      })
      
      if (res.ok) {
        setNewAttackOpen(false)
        fetchData()
      } else {
        const error = await res.json()
        alert(`Failed to start attack: ${error.error}`)
      }
    } catch (_error) {
      alert('Failed to start attack')
    } finally {
      setStartingAttack(false)
    }
  }

  // Convert vectors to display format
  const vectorList: AttackVector[] = Object.entries(vectors)
    .filter(([name]) => name !== 'Total')
    .map(([name, count]) => ({
      name: name.replace('_', ' '),
      count: count as number,
      severity: (name.includes('Injection') || name.includes('Jailbreak') ? 'critical' : 
                name.includes('Exfiltration') || name.includes('Poison') ? 'high' : 'medium') as 'critical' | 'high' | 'medium' | 'low'
    }))
    .sort((a, b) => b.count - a.count)

  const filteredVectors = vectorList.filter(v => 
    v.name.toLowerCase().includes(search.toLowerCase())
  )

  const isOnline = health?.status === 'healthy'
  const totalVectors = vectors['Total'] || Object.values(vectors).reduce((a, b) => a + (b as number), 0)
  const activeAttacks = attacks.filter(a => a.state === 'running' || a.state === 'paused').length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Crosshair className="w-7 h-7 text-red-400" />
            STRIKE Platform
          </h1>
          <p className="text-gray-400 text-sm">AI Red Team — Attack Simulation Platform</p>
        </div>
        <div className="flex gap-3 items-center">
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm ${
            isOnline ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
          }`}>
            {isOnline ? <Wifi className="w-4 h-4" /> : <WifiOff className="w-4 h-4" />}
            {isOnline ? 'Online' : 'Offline'}
          </div>
          
          <button 
            onClick={fetchData}
            className="flex items-center gap-2 px-4 py-2 border border-[#374151] rounded-lg hover:border-purple-500 transition-colors"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button 
            onClick={() => setNewAttackOpen(true)}
            disabled={!isOnline}
            className="flex items-center gap-2 px-4 py-2 bg-red-500 hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed rounded-lg transition-colors"
          >
            <Play className="w-4 h-4" />
            New Attack
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4">
        {/* Total Payloads with breakdown */}
        <div className="bg-[#1a1f2e] rounded-xl border border-[#374151] p-4 group relative">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-red-500/20">
              <Crosshair className="w-5 h-5 text-red-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">
                {payloads.total > 0 ? payloads.total.toLocaleString() : totalVectors}
              </p>
              <p className="text-sm text-gray-400">Total Payloads</p>
            </div>
          </div>
          {/* Breakdown tooltip */}
          {payloads.total > 0 && (
            <div className="absolute left-0 right-0 top-full mt-2 p-3 bg-[#111827] border border-[#374151] rounded-lg opacity-0 group-hover:opacity-100 transition-opacity z-10 text-xs space-y-1">
              <div className="flex justify-between">
                <span className="text-purple-400">🧠 LLM Vectors</span>
                <span>{payloads.llm_vectors}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-orange-400">🛡️ Jailbreaks</span>
                <span>{payloads.jailbreaks.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-red-400">🌐 Web Payloads</span>
                <span>{payloads.web_payloads.toLocaleString()}</span>
              </div>
            </div>
          )}
        </div>
        <div className="bg-[#1a1f2e] rounded-xl border border-[#374151] p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-orange-500/20">
              <Activity className="w-5 h-5 text-orange-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">{activeAttacks}</p>
              <p className="text-sm text-gray-400">Active Attacks</p>
            </div>
          </div>
        </div>
        <div className="bg-[#1a1f2e] rounded-xl border border-[#374151] p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-green-500/20">
              <Zap className="w-5 h-5 text-green-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">{attacks.length}</p>
              <p className="text-sm text-gray-400">Total Campaigns</p>
            </div>
          </div>
        </div>
        <div className="bg-[#1a1f2e] rounded-xl border border-[#374151] p-4">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${isOnline ? 'bg-green-500/20' : 'bg-red-500/20'}`}>
              {isOnline ? <CheckCircle className="w-5 h-5 text-green-400" /> : <AlertTriangle className="w-5 h-5 text-red-400" />}
            </div>
            <div>
              <p className="text-2xl font-bold">{isOnline ? 'Ready' : 'Offline'}</p>
              <p className="text-sm text-gray-400">Strike Status</p>
            </div>
          </div>
        </div>
      </div>

      {/* Active Campaigns */}
      {attacks.length > 0 && (
        <div className="bg-[#1a1f2e] rounded-xl border border-[#374151] p-4">
          <h2 className="font-semibold mb-4 flex items-center gap-2">
            <Target className="w-5 h-5 text-red-400" />
            Campaigns ({attacks.length})
          </h2>
          <div className="space-y-3">
            {attacks.map(attack => (
              <CampaignCard
                key={attack.id}
                attack={attack}
                onStop={() => stopAttack(attack.id)}
                onPause={() => pauseAttack(attack.id)}
                onResume={() => resumeAttack(attack.id)}
                expanded={expandedAttack === attack.id}
                onToggle={() => setExpandedAttack(expandedAttack === attack.id ? null : attack.id)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search attack vectors..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-[#1a1f2e] rounded-lg border border-[#374151] focus:border-purple-500 focus:outline-none"
          />
        </div>
      </div>

      {/* Vectors Grid */}
      <div className="grid grid-cols-3 gap-4">
        {loading ? (
          <div className="col-span-3 flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-purple-400" />
          </div>
        ) : filteredVectors.length === 0 ? (
          <div className="col-span-3 text-center py-12 text-gray-400">
            {isOnline ? 'No attack vectors found' : 'Strike API is offline'}
          </div>
        ) : (
          filteredVectors.map((vector) => (
            <div 
              key={vector.name}
              className="bg-[#1a1f2e] rounded-xl border border-[#374151] p-4 hover:border-red-500/50 transition-all cursor-pointer"
            >
              <div className="flex justify-between items-start mb-3">
                <div>
                  <h3 className="font-semibold">{vector.name}</h3>
                  <span className="text-xs text-gray-400">{vector.count} payloads</span>
                </div>
                <span className={`px-2 py-1 rounded text-xs font-medium border ${severityConfig[vector.severity]}`}>
                  {vector.severity.toUpperCase()}
                </span>
              </div>
              <div className="h-2 bg-[#374151] rounded-full overflow-hidden">
                <div 
                  className={`h-full ${
                    vector.severity === 'critical' ? 'bg-red-500' :
                    vector.severity === 'high' ? 'bg-orange-500' : 'bg-yellow-500'
                  }`}
                  style={{ width: `${Math.min(vector.count * 3, 100)}%` }}
                />
              </div>
            </div>
          ))
        )}
      </div>

      {/* New Attack Modal */}
      <NewAttackModal
        isOpen={newAttackOpen}
        onClose={() => setNewAttackOpen(false)}
        onStart={startAttack}
        loading={startingAttack}
      />
    </div>
  )
}
