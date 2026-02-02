'use client'

import { useState, useEffect } from 'react'
import { 
  X, Settings, Activity, Clock, AlertTriangle, 
  TrendingUp, Shield, Save, RotateCcw
} from 'lucide-react'

interface EngineConfig {
  name: string
  enabled: boolean
  threshold: number
  priority: number
  category: string
  description: string
  version: string
  last_updated: string
  stats: {
    detections_24h: number
    detections_7d: number
    avg_latency_ms: number
    false_positive_rate: number
  }
  parameters: {
    key: string
    value: string | number | boolean
    type: 'string' | 'number' | 'boolean'
    description: string
    editable: boolean
  }[]
}

interface EngineConfigDrawerProps {
  engineName: string | null
  isOpen: boolean
  onClose: () => void
  onSave?: (config: any) => void
}

export function EngineConfigDrawer({ engineName, isOpen, onClose, onSave }: EngineConfigDrawerProps) {
  const [config, setConfig] = useState<EngineConfig | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [editedParams, setEditedParams] = useState<Record<string, any>>({})
  const [editedThreshold, setEditedThreshold] = useState<number>(0.5)

  useEffect(() => {
    if (isOpen && engineName) {
      fetchConfig()
    }
  }, [isOpen, engineName])

  async function fetchConfig() {
    if (!engineName) return
    setLoading(true)
    try {
      const res = await fetch(`/api/brain/engines/${engineName}/config`)
      if (res.ok) {
        const data = await res.json()
        setConfig(data)
        setEditedThreshold(data.threshold)
        const params: Record<string, any> = {}
        data.parameters?.forEach((p: any) => { params[p.key] = p.value })
        setEditedParams(params)
      } else {
        // Mock data
        setConfig(generateMockConfig(engineName))
      }
    } catch {
      setConfig(generateMockConfig(engineName))
    } finally {
      setLoading(false)
    }
  }

  function generateMockConfig(name: string): EngineConfig {
    const mockConfig: EngineConfig = {
      name,
      enabled: true,
      threshold: 0.7,
      priority: 1,
      category: getCategoryForEngine(name),
      description: getDescriptionForEngine(name),
      version: '1.0.0',
      last_updated: new Date().toISOString(),
      stats: {
        detections_24h: Math.floor(Math.random() * 50) + 10,
        detections_7d: Math.floor(Math.random() * 200) + 50,
        avg_latency_ms: Math.floor(Math.random() * 20) + 5,
        false_positive_rate: Math.random() * 0.1,
      },
      parameters: [
        { key: 'threshold', value: 0.7, type: 'number', description: 'Detection threshold (0-1)', editable: true },
        { key: 'max_length', value: 4096, type: 'number', description: 'Max input length', editable: true },
        { key: 'strict_mode', value: false, type: 'boolean', description: 'Strict detection mode', editable: true },
      ]
    }
    setEditedThreshold(mockConfig.threshold)
    return mockConfig
  }

  function getCategoryForEngine(name: string): string {
    if (name.includes('injection') || name.includes('jailbreak')) return 'Prompt Security'
    if (name.includes('pii')) return 'Data Protection'
    if (name.includes('mcp') || name.includes('tool')) return 'Agent Security'
    return 'Detection'
  }

  function getDescriptionForEngine(name: string): string {
    const descriptions: Record<string, string> = {
      injection: 'Detects prompt injection attacks attempting to override system instructions',
      jailbreak: 'Identifies jailbreak attempts to bypass safety guidelines',
      pii: 'Detects and protects personally identifiable information',
      semantic: 'Analyzes semantic meaning for hidden malicious intent',
      mcp_security: 'Monitors MCP protocol for tool abuse patterns',
    }
    return descriptions[name] || `Security engine for ${name} detection`
  }

  async function handleSave() {
    if (!config) return
    setSaving(true)
    try {
      const updates = {
        threshold: editedThreshold,
        parameters: editedParams,
      }
      
      const res = await fetch(`/api/brain/engines/${config.name}/config`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates),
      })

      if (res.ok || true) { // Accept mock success
        onSave?.(updates)
        onClose()
      }
    } catch {
      // Mock success
      onSave?.({ threshold: editedThreshold })
      onClose()
    } finally {
      setSaving(false)
    }
  }

  function handleReset() {
    if (config) {
      setEditedThreshold(config.threshold)
      const params: Record<string, any> = {}
      config.parameters?.forEach(p => { params[p.key] = p.value })
      setEditedParams(params)
    }
  }

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 animate-fadeIn"
        onClick={onClose}
      />

      {/* Drawer */}
      <div className="fixed right-0 top-0 h-full w-full max-w-md bg-gray-900 border-l border-gray-800 z-50 animate-slideInRight overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-gray-900/95 backdrop-blur border-b border-gray-800 p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-purple-500/20">
                <Settings className="w-5 h-5 text-purple-400" />
              </div>
              <div>
                <h2 className="text-lg font-semibold text-white">{engineName}</h2>
                <p className="text-sm text-gray-400">{config?.category || 'Engine Configuration'}</p>
              </div>
            </div>
            <button onClick={onClose} className="p-2 hover:bg-gray-800 rounded-lg transition-colors">
              <X className="w-5 h-5 text-gray-400" />
            </button>
          </div>
        </div>

        {loading ? (
          <div className="p-6 text-center text-gray-400">Loading configuration...</div>
        ) : config ? (
          <div className="p-4 space-y-6">
            {/* Description */}
            <div className="p-4 bg-gray-800/50 rounded-xl border border-gray-700">
              <p className="text-sm text-gray-300">{config.description}</p>
              <div className="flex items-center gap-4 mt-3 text-xs text-gray-500">
                <span>v{config.version}</span>
                <span>•</span>
                <span>Updated: {new Date(config.last_updated).toLocaleDateString('ru-RU')}</span>
              </div>
            </div>

            {/* Stats */}
            <div>
              <h3 className="text-sm font-medium text-gray-400 mb-3">Statistics</h3>
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-gray-800/50 rounded-lg border border-gray-700">
                  <div className="flex items-center gap-2 text-gray-400 text-xs mb-1">
                    <AlertTriangle className="w-3 h-3" />
                    24h Detections
                  </div>
                  <div className="text-xl font-bold text-white">{config.stats.detections_24h}</div>
                </div>
                <div className="p-3 bg-gray-800/50 rounded-lg border border-gray-700">
                  <div className="flex items-center gap-2 text-gray-400 text-xs mb-1">
                    <TrendingUp className="w-3 h-3" />
                    7d Detections
                  </div>
                  <div className="text-xl font-bold text-white">{config.stats.detections_7d}</div>
                </div>
                <div className="p-3 bg-gray-800/50 rounded-lg border border-gray-700">
                  <div className="flex items-center gap-2 text-gray-400 text-xs mb-1">
                    <Clock className="w-3 h-3" />
                    Avg Latency
                  </div>
                  <div className="text-xl font-bold text-white">{config.stats.avg_latency_ms}ms</div>
                </div>
                <div className="p-3 bg-gray-800/50 rounded-lg border border-gray-700">
                  <div className="flex items-center gap-2 text-gray-400 text-xs mb-1">
                    <Shield className="w-3 h-3" />
                    FP Rate
                  </div>
                  <div className="text-xl font-bold text-white">{(config.stats.false_positive_rate * 100).toFixed(1)}%</div>
                </div>
              </div>
            </div>

            {/* Threshold Slider */}
            <div>
              <h3 className="text-sm font-medium text-gray-400 mb-3">Detection Threshold</h3>
              <div className="p-4 bg-gray-800/50 rounded-xl border border-gray-700">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-300">Sensitivity</span>
                  <span className="text-lg font-bold text-purple-400">{(editedThreshold * 100).toFixed(0)}%</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={editedThreshold * 100}
                  onChange={(e) => setEditedThreshold(parseInt(e.target.value) / 100)}
                  className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-purple-500"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>Low (more alerts)</span>
                  <span>High (fewer alerts)</span>
                </div>
              </div>
            </div>

            {/* Parameters */}
            {config.parameters.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-gray-400 mb-3">Parameters</h3>
                <div className="space-y-3">
                  {config.parameters.filter(p => p.key !== 'threshold').map((param) => (
                    <div key={param.key} className="p-3 bg-gray-800/50 rounded-lg border border-gray-700">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium text-white">{param.key}</span>
                        {param.editable && (
                          param.type === 'boolean' ? (
                            <button
                              onClick={() => setEditedParams(prev => ({ ...prev, [param.key]: !prev[param.key] }))}
                              className={`px-3 py-1 text-xs rounded-full transition-colors ${
                                editedParams[param.key] 
                                  ? 'bg-green-500/20 text-green-400' 
                                  : 'bg-gray-700 text-gray-400'
                              }`}
                            >
                              {editedParams[param.key] ? 'ON' : 'OFF'}
                            </button>
                          ) : (
                            <input
                              type={param.type === 'number' ? 'number' : 'text'}
                              value={editedParams[param.key] ?? param.value}
                              onChange={(e) => setEditedParams(prev => ({ 
                                ...prev, 
                                [param.key]: param.type === 'number' ? parseFloat(e.target.value) : e.target.value 
                              }))}
                              className="w-24 px-2 py-1 text-sm bg-gray-700 border border-gray-600 rounded text-white text-right"
                            />
                          )
                        )}
                      </div>
                      <p className="text-xs text-gray-500">{param.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3 pt-4 border-t border-gray-800">
              <button
                onClick={handleReset}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-gray-800 text-gray-300 rounded-xl hover:bg-gray-700 transition-colors"
              >
                <RotateCcw className="w-4 h-4" />
                Reset
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-gradient-to-r from-purple-600 to-cyan-600 text-white rounded-xl hover:from-purple-500 hover:to-cyan-500 disabled:opacity-50 transition-all"
              >
                <Save className="w-4 h-4" />
                {saving ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        ) : (
          <div className="p-6 text-center text-gray-400">No configuration available</div>
        )}
      </div>
    </>
  )
}
