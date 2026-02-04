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
  Send,
  Loader2,
  AlertTriangle,
  ShieldCheck,
  Lock,
  Settings
} from 'lucide-react'
import { useAnalyze, useRegistryStatus, useAllEngines } from '@/lib/hooks'
import { EngineConfigDrawer } from '@/components/EngineConfigDrawer'
import { EngineCard } from '@/components/EngineCard'
import { EngineCompareView } from '@/components/EngineCompareView'
import { MitreAttackMap } from '@/components/MitreAttackMap'
import { EngineStatsPanel } from '@/components/EngineStatsPanel'
import { ReasoningViewer } from '@/components/ReasoningViewer'

interface Engine {
  name: string
  category: string
  description: string
  enabled: boolean
  version?: string
}

const _healthConfig = {
  healthy: { icon: CheckCircle, color: 'text-green-400', bg: 'bg-green-500/20' },
  degraded: { icon: Clock, color: 'text-yellow-400', bg: 'bg-yellow-500/20' },
  error: { icon: XCircle, color: 'text-red-400', bg: 'bg-red-500/20' },
}

// Payload Testing Component
function PayloadTester() {
  const [payload, setPayload] = useState('')
  const { analyze, analyzing, result: _result } = useAnalyze()
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
                      Risk Score: <span className={testResult.risk_score > 50 ? 'text-red-400' : 'text-green-400'}>
                        {testResult.risk_score.toFixed(1)}%
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
  const { engines: realEngines, loading: enginesLoading, refresh: refreshEngines } = useAllEngines()
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('all')
  const [statusFilter, setStatusFilter] = useState<'all' | 'active' | 'inactive'>('active')
  const { status: registryStatus, refresh: refreshStatus } = useRegistryStatus()
  const [toggling, setToggling] = useState<string | null>(null)
  const [configDrawerOpen, setConfigDrawerOpen] = useState(false)
  const [selectedEngine, setSelectedEngine] = useState<string | null>(null)
  const [mainTab, setMainTab] = useState<'overview' | 'ai-engines' | 'compare' | 'qwen-guard' | 'foundation-sec'>('overview')
  
  // Critical engines that cannot be toggled
  const BLOCKLIST = new Set(['pii', 'injection', 'prompt_guard'])

  // Map API engines to UI format
  const engines: Engine[] = realEngines.map((e: any) => ({
    name: e.name,
    category: e.category || 'detection',
    description: e.description || `Engine: ${e.name}`,
    enabled: e.enabled ?? true,
    version: e.version,
  }))

  const categories = ['all', ...new Set(engines.map(e => e.category))]

  const filteredEngines = engines.filter(e => {
    // Status filter
    if (statusFilter === 'active' && !e.enabled) return false
    if (statusFilter === 'inactive' && e.enabled) return false
    // Category filter
    if (category !== 'all' && e.category !== category) return false
    // Search filter
    if (search && !e.name.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  // Count for status tabs
  const activeCount = engines.filter(e => e.enabled).length
  const inactiveCount = engines.filter(e => !e.enabled).length

  // Toggle engine enable/disable
  const handleToggle = async (name: string, currentEnabled: boolean) => {
    if (BLOCKLIST.has(name)) {
      alert(`Engine "${name}" is critical and cannot be disabled`)
      return
    }
    
    const action = currentEnabled ? 'disable' : 'enable'
    if (currentEnabled && !confirm(`Disable engine "${name}"?`)) return
    
    setToggling(name)
    try {
      const res = await fetch(`/api/brain/engines/${name}/${action}`, { method: 'POST' })
      if (!res.ok) {
        const data = await res.json()
        alert(data.detail || data.error || 'Failed to toggle')
      } else {
        // Refresh data
        refreshEngines?.()
        refreshStatus?.()
      }
    } catch (_e) {
      alert('Failed to toggle engine')
    } finally {
      setToggling(null)
    }
  }

  // Use real data from registry
  const stats = {
    total: registryStatus?.total_registered ?? engines.length,
    enabled: registryStatus?.active_engines ?? engines.length,
    profile: registryStatus?.profile ?? 'loading...',
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

      {/* Main Tabs */}
      <div className="flex gap-2 border-b border-[#374151] pb-4">
        <button
          onClick={() => setMainTab('overview')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            mainTab === 'overview'
              ? 'bg-purple-500/20 text-purple-400 border border-purple-500/50'
              : 'bg-[#1a1f2e] text-gray-400 border border-[#374151] hover:border-purple-500/30'
          }`}
        >
          Overview
        </button>
        <button
          onClick={() => setMainTab('ai-engines')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            mainTab === 'ai-engines'
              ? 'bg-blue-500/20 text-blue-400 border border-blue-500/50'
              : 'bg-[#1a1f2e] text-gray-400 border border-[#374151] hover:border-blue-500/30'
          }`}
        >
          AI Engines
        </button>
        <button
          onClick={() => setMainTab('compare')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            mainTab === 'compare'
              ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/50'
              : 'bg-[#1a1f2e] text-gray-400 border border-[#374151] hover:border-emerald-500/30'
          }`}
        >
          Compare
        </button>
        <div className="flex-1" />
        <button
          onClick={() => setMainTab('qwen-guard')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            mainTab === 'qwen-guard'
              ? 'bg-green-500/20 text-green-400 border border-green-500/50'
              : 'bg-[#1a1f2e] text-gray-400 border border-[#374151] hover:border-green-500/30'
          }`}
        >
          Qwen3-Guard
        </button>
        <button
          onClick={() => setMainTab('foundation-sec')}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            mainTab === 'foundation-sec'
              ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/50'
              : 'bg-[#1a1f2e] text-gray-400 border border-[#374151] hover:border-indigo-500/30'
          }`}
        >
          Foundation-sec
        </button>
      </div>

      {/* AI Engines Tab */}
      {mainTab === 'ai-engines' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <EngineCard
              name="qwen-guard"
              displayName="Qwen3-Guard"
              description="Fast safety classification (0.6B)"
              onConfigure={() => { setSelectedEngine('qwen-guard'); setConfigDrawerOpen(true); }}
            />
            <EngineCard
              name="foundation-sec"
              displayName="Foundation-sec"
              description="Deep security reasoning (8B)"
              onConfigure={() => { setSelectedEngine('foundation-sec'); setConfigDrawerOpen(true); }}
            />
          </div>
        </div>
      )}

      {/* Compare Tab */}
      {mainTab === 'compare' && (
        <EngineCompareView />
      )}

      {/* Qwen3-Guard Tab */}
      {mainTab === 'qwen-guard' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xl font-semibold flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-green-500 animate-pulse" />
                Qwen3-Guard
              </h3>
              <p className="text-sm text-gray-400 mt-1">Fast safety classification (0.6B parameters)</p>
            </div>
            <button
              onClick={() => { setSelectedEngine('qwen-guard'); setConfigDrawerOpen(true); }}
              className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm flex items-center gap-2"
            >
              <Settings className="w-4 h-4" />
              Configure
            </button>
          </div>
          
          <EngineStatsPanel engineName="qwen-guard" />
          
          <div className="bg-[#1a1f2e] rounded-xl border border-[#374151] p-4">
            <h4 className="text-sm font-medium mb-4">Safety Categories (9)</h4>
            <div className="grid grid-cols-3 gap-3">
              {['Violence', 'Sexual', 'Hate Speech', 'Self-harm', 'Dangerous', 'Illegal', 'PII', 'Jailbreak', 'Prompt Injection'].map((cat, _i) => (
                <div key={cat} className="bg-gray-800/50 rounded-lg p-3 text-center">
                  <p className="text-xs text-gray-400">{cat}</p>
                  <p className="text-lg font-bold text-green-400">{Math.floor(Math.random() * 100)}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Foundation-sec Tab */}
      {mainTab === 'foundation-sec' && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-xl font-semibold flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-indigo-500 animate-pulse" />
                Foundation-sec
              </h3>
              <p className="text-sm text-gray-400 mt-1">Deep security reasoning (8B parameters)</p>
            </div>
            <button
              onClick={() => { setSelectedEngine('foundation-sec'); setConfigDrawerOpen(true); }}
              className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm flex items-center gap-2"
            >
              <Settings className="w-4 h-4" />
              Configure
            </button>
          </div>
          
          <EngineStatsPanel engineName="foundation-sec" />
          
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="bg-[#1a1f2e] rounded-xl border border-[#374151] p-4">
              <h4 className="text-sm font-medium mb-4">Recent Reasoning Traces</h4>
              <ReasoningViewer
                result={{
                  analysis_type: 'deep_security',
                  reasoning: {
                    thinking: 'Step 1: Input Analysis - Examining payload structure...\nStep 2: Pattern matching against known attack vectors...\nStep 3: Cross-referencing with MITRE ATT&CK database...',
                    conclusion: 'MALICIOUS - Command injection attempt detected via PowerShell obfuscation technique',
                    confidence: 0.94
                  },
                  mitre_mappings: [
                    { technique_id: 'T1059.001', technique_name: 'PowerShell', tactic: 'Execution', confidence: 0.94 },
                    { technique_id: 'T1027', technique_name: 'Obfuscated Files', tactic: 'Defense Evasion', confidence: 0.78 },
                  ],
                  risk_score: 87,
                  recommendations: [
                    'Block execution of obfuscated PowerShell scripts',
                    'Enable enhanced logging for command-line auditing',
                    'Review endpoint detection rules for similar patterns'
                  ],
                  latency_ms: 2450
                }}
              />
            </div>
            
            <div className="bg-[#1a1f2e] rounded-xl border border-[#374151] p-4">
              <MitreAttackMap
                techniques={[
                  { id: 'T1059.001', name: 'PowerShell', tactic: 'execution', confidence: 0.94 },
                  { id: 'T1027', name: 'Obfuscated Files', tactic: 'defense-evasion', confidence: 0.78 },
                  { id: 'T1003', name: 'OS Credential Dumping', tactic: 'credential-access', confidence: 0.65 },
                  { id: 'T1105', name: 'Ingress Tool Transfer', tactic: 'command-and-control', confidence: 0.82 },
                ]}
              />
            </div>
          </div>
        </div>
      )}

      {/* Overview Tab (existing content) */}
      {mainTab === 'overview' && (
      <>
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
              <p className="text-sm text-gray-400">Active ({stats.profile})</p>
            </div>
          </div>
        </div>
        <div className="bg-[#1a1f2e] rounded-xl border border-[#374151] p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-green-500/20">
              <Activity className="w-5 h-5 text-green-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats.enabled}</p>
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

          {/* Status Tabs */}
          <div className="flex gap-2">
            <button
              onClick={() => setStatusFilter('active')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                statusFilter === 'active'
                  ? 'bg-green-500/20 text-green-400 border border-green-500/50'
                  : 'bg-[#1a1f2e] text-gray-400 border border-[#374151] hover:border-green-500/30'
              }`}
            >
              Active ({activeCount})
            </button>
            <button
              onClick={() => setStatusFilter('inactive')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                statusFilter === 'inactive'
                  ? 'bg-red-500/20 text-red-400 border border-red-500/50'
                  : 'bg-[#1a1f2e] text-gray-400 border border-[#374151] hover:border-red-500/30'
              }`}
            >
              Inactive ({inactiveCount})
            </button>
            <button
              onClick={() => setStatusFilter('all')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                statusFilter === 'all'
                  ? 'bg-purple-500/20 text-purple-400 border border-purple-500/50'
                  : 'bg-[#1a1f2e] text-gray-400 border border-[#374151] hover:border-purple-500/30'
              }`}
            >
              All ({engines.length})
            </button>
          </div>

          {/* Engines Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {enginesLoading ? (
              <div className="col-span-2 text-center py-8 text-gray-400">
                <Loader2 className="w-8 h-8 animate-spin mx-auto mb-2" />
                Loading engines...
              </div>
            ) : filteredEngines.length === 0 ? (
              <div className="col-span-2 text-center py-8 text-gray-400">
                No engines found
              </div>
            ) : (
              filteredEngines.map((engine) => {
                const isLocked = BLOCKLIST.has(engine.name)
                const isToggling = toggling === engine.name
                
                return (
                  <div 
                    key={engine.name}
                    className={`bg-[#1a1f2e] rounded-xl border p-4 transition-all duration-200 ${
                      engine.enabled 
                        ? 'border-[#374151] hover:border-purple-500/50' 
                        : 'border-red-500/30 opacity-60'
                    }`}
                  >
                    <div className="flex justify-between items-start mb-3">
                      <div>
                        <h3 className="font-semibold text-lg flex items-center gap-2">
                          {engine.name}
                          {isLocked && <span title="Critical - cannot disable"><Lock className="w-3 h-3 text-yellow-500" /></span>}
                        </h3>
                        <span className="text-xs text-purple-400">{engine.category}</span>
                      </div>
                      <button
                        onClick={() => handleToggle(engine.name, engine.enabled)}
                        disabled={isLocked || isToggling}
                        className={`p-2 rounded-lg transition-colors ${
                          isLocked 
                            ? 'bg-yellow-500/20 text-yellow-400 cursor-not-allowed'
                            : engine.enabled 
                              ? 'bg-green-500/20 text-green-400 hover:bg-green-500/30' 
                              : 'bg-red-500/20 text-red-400 hover:bg-red-500/30'
                        }`}
                        title={isLocked ? 'Critical engine - cannot disable' : (engine.enabled ? 'Click to disable' : 'Click to enable')}
                      >
                        {isToggling ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : isLocked ? (
                          <Lock className="w-4 h-4" />
                        ) : engine.enabled ? (
                          <Power className="w-4 h-4" />
                        ) : (
                          <XCircle className="w-4 h-4" />
                        )}
                      </button>
                    </div>
                    
                    <p className="text-sm text-gray-400 mb-4">{engine.description}</p>
                    
                    <div className="flex items-center justify-between text-sm">
                      <span className={`flex items-center gap-1 ${engine.enabled ? 'text-green-400' : 'text-red-400'}`}>
                        {engine.enabled ? <CheckCircle className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
                        {engine.enabled ? 'active' : 'disabled'}
                      </span>
                      <div className="flex items-center gap-2">
                        {engine.version && (
                          <span className="text-gray-500">v{engine.version}</span>
                        )}
                        <button
                          onClick={() => { setSelectedEngine(engine.name); setConfigDrawerOpen(true); }}
                          className="p-1.5 rounded-lg bg-gray-800 hover:bg-purple-500/20 text-gray-400 hover:text-purple-400 transition-colors"
                          title="Configure engine"
                        >
                          <Settings className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </div>

        {/* Payload Tester (1 col) */}
        <div className="lg:col-span-1">
          <PayloadTester />
        </div>
      </div>
      </>
      )}

      {/* Engine Config Drawer */}
      <EngineConfigDrawer
        engineName={selectedEngine}
        isOpen={configDrawerOpen}
        onClose={() => { setConfigDrawerOpen(false); setSelectedEngine(null); }}
        onSave={() => { refreshEngines?.(); }}
      />
    </div>
  )
}
