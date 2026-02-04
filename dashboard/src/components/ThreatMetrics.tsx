'use client'

import { useState, useEffect } from 'react'
import { Activity, Shield, AlertTriangle, TrendingUp } from 'lucide-react'

interface ThreatData {
  timestamp: string
  total: number
  blocked: number
  allowed: number
}

interface EngineActivity {
  name: string
  detections: number
  lastActive: string
}

export function ThreatMetrics() {
  const [period, setPeriod] = useState<'24h' | '7d' | '30d'>('24h')
  const [threatData, setThreatData] = useState<ThreatData[]>([])
  const [engineActivity, setEngineActivity] = useState<EngineActivity[]>([])
  const [_loading, setLoading] = useState(true)

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 10000) // Refresh every 10s
    return () => clearInterval(interval)
  }, [period])

  async function fetchData() {
    try {
      // Fetch Shield stats for real metrics
      const [statsRes, historyRes, guardsRes] = await Promise.all([
        fetch('/api/shield/stats'),
        fetch('/api/shield/history'),
        fetch('/api/shield/guards'),
      ])
      
      if (statsRes.ok && historyRes.ok) {
        const stats = await statsRes.json()
        const history = await historyRes.json()
        
        // Build trend data from history timestamps
        const now = Date.now()
        const periodMs = period === '24h' ? 86400000 : period === '7d' ? 604800000 : 2592000000
        const buckets = period === '24h' ? 24 : period === '7d' ? 7 : 30
        const bucketSize = periodMs / buckets
        
        const trends: ThreatData[] = Array.from({ length: buckets }, (_, i) => ({
          timestamp: new Date(now - (buckets - i) * bucketSize).toISOString(),
          total: 0,
          blocked: 0,
          allowed: 0,
        }))
        
        // Count history items into buckets
        ;(history || []).forEach((h: any) => {
          const ts = h.timestamp * 1000
          const age = now - ts
          if (age < periodMs) {
            const bucketIdx = Math.floor((periodMs - age) / bucketSize)
            if (bucketIdx >= 0 && bucketIdx < buckets) {
              trends[bucketIdx].total++
              if (h.verdict === 'block') trends[bucketIdx].blocked++
              else if (h.verdict === 'allow') trends[bucketIdx].allowed++
            }
          }
        })
        
        // Add current stats to last bucket
        if (trends.length > 0) {
          trends[trends.length - 1].total = stats.requests?.total || 0
          trends[trends.length - 1].blocked = stats.requests?.blocked || 0
          trends[trends.length - 1].allowed = stats.requests?.allowed || 0
        }
        
        setThreatData(trends)
        
        // Build engine activity from guards
        if (guardsRes.ok) {
          const guards = await guardsRes.json()
          const activity: EngineActivity[] = Object.entries(guards)
            .map(([name, g]: [string, any]) => ({
              name: g.name || name,
              detections: g.blocks || g.checks || 0,
              lastActive: new Date().toISOString(),
            }))
            .filter(e => e.detections > 0)
            .sort((a, b) => b.detections - a.detections)
            .slice(0, 5)
          setEngineActivity(activity)
        }
      } else {
        // Fallback to Brain API
        const res = await fetch(`/api/brain/metrics?period=${period}`)
        if (res.ok) {
          const data = await res.json()
          setThreatData(data.trends || [])
          setEngineActivity(data.engines || [])
        }
      }
    } catch {
      // Keep existing data on error
    } finally {
      setLoading(false)
    }
  }


  const totalThreats = threatData.reduce((acc, d) => acc + d.total, 0)
  const blockedThreats = threatData.reduce((acc, d) => acc + d.blocked, 0)
  const blockRate = totalThreats > 0 ? (blockedThreats / totalThreats * 100).toFixed(1) : '0'
  const maxValue = Math.max(...threatData.map(d => d.total), 1)

  return (
    <div className="card">
      <div className="card-header">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="icon-container icon-container--warning">
              <Activity className="w-5 h-5" />
            </div>
            <div>
              <h3 className="card-title">Threat Metrics</h3>
              <p className="card-subtitle">Real-time detection activity</p>
            </div>
          </div>
          
          <div className="flex gap-1">
            {(['24h', '7d', '30d'] as const).map(p => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`px-3 py-1 text-sm rounded-lg transition-colors ${
                  period === p 
                    ? 'bg-purple-500/20 text-purple-400 border border-purple-500/30' 
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="card-content">
        {/* Stats Row */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-gray-900/50 rounded-xl p-4 border border-gray-800">
            <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
              <AlertTriangle className="w-4 h-4" />
              Total
            </div>
            <div className="text-2xl font-bold text-white">{totalThreats}</div>
          </div>
          <div className="bg-gray-900/50 rounded-xl p-4 border border-gray-800">
            <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
              <Shield className="w-4 h-4 text-green-400" />
              Blocked
            </div>
            <div className="text-2xl font-bold text-green-400">{blockedThreats}</div>
          </div>
          <div className="bg-gray-900/50 rounded-xl p-4 border border-gray-800">
            <div className="flex items-center gap-2 text-gray-400 text-sm mb-1">
              <TrendingUp className="w-4 h-4 text-blue-400" />
              Block Rate
            </div>
            <div className="text-2xl font-bold text-blue-400">{blockRate}%</div>
          </div>
        </div>

        {/* Mini Chart */}
        <div className="relative h-32 mb-6">
          <div className="absolute inset-0 flex items-end gap-[2px]">
            {threatData.map((d, i) => (
              <div
                key={i}
                className="flex-1 bg-gradient-to-t from-purple-500/60 to-purple-400/30 rounded-t transition-all hover:from-purple-400 hover:to-purple-300/50"
                style={{ height: `${(d.total / maxValue) * 100}%` }}
                title={`${d.total} threats`}
              />
            ))}
          </div>
          <div className="absolute bottom-0 left-0 right-0 border-t border-gray-700/50" />
        </div>

        {/* Top Engines */}
        <div>
          <h4 className="text-sm font-medium text-gray-400 mb-3">Top Active Engines</h4>
          <div className="space-y-2">
            {engineActivity.map((engine, i) => (
              <div key={engine.name} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-500 w-4">{i + 1}</span>
                  <span className="text-sm text-gray-200">{engine.name}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-24 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-gradient-to-r from-purple-500 to-cyan-400 rounded-full"
                      style={{ width: `${Math.min(100, (engine.detections / 50) * 100)}%` }}
                    />
                  </div>
                  <span className="text-xs text-gray-400 w-8 text-right">{engine.detections}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
