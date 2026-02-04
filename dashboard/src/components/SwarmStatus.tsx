'use client'

/**
 * SwarmStatus Component
 * 
 * Displays real-time status of the BRAIN swarm:
 * - Online/offline node count
 * - Aggregated statistics
 * - Pattern sharing status
 */

import { useState, useEffect } from 'react'
import { Circle, Server, Activity, Shield, Clock } from 'lucide-react'

interface SwarmNode {
  node_id: string
  hostname: string
  port: number
  version: string
  status: 'online' | 'degraded' | 'offline'
  capabilities: string[]
  last_heartbeat: string
}

interface SwarmStats {
  nodes: {
    online: number
    offline: number
    degraded: number
  }
  total_analyses: number
  total_blocked: number
  patterns_shared: number
  avg_latency_ms: number
}

interface SwarmData {
  nodes: SwarmNode[]
  stats: SwarmStats | null
  loading: boolean
  error: string | null
}

function useSwarmData(): SwarmData {
  const [nodes, setNodes] = useState<SwarmNode[]>([])
  const [stats, setStats] = useState<SwarmStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchData() {
      try {
        const [nodesRes, statsRes] = await Promise.all([
          fetch('/api/swarm/nodes'),
          fetch('/api/swarm/stats'),
        ])

        if (nodesRes.ok) {
          const data = await nodesRes.json()
          setNodes(data.nodes || [])
        }

        if (statsRes.ok) {
          setStats(await statsRes.json())
        }

        setError(null)
      } catch (_err) {
        setError('Failed to fetch swarm data')
      } finally {
        setLoading(false)
      }
    }

    fetchData()
    const interval = setInterval(fetchData, 10000) // Refresh every 10s
    return () => clearInterval(interval)
  }, [])

  return { nodes, stats, loading, error }
}

const statusColors = {
  online: 'text-emerald-500',
  degraded: 'text-yellow-500',
  offline: 'text-red-500',
}

const statusBg = {
  online: 'bg-emerald-500/10',
  degraded: 'bg-yellow-500/10',
  offline: 'bg-red-500/10',
}

export function SwarmStatus() {
  const { nodes, stats, loading, error } = useSwarmData()

  if (loading) {
    return (
      <div className="bg-[#111827] rounded-xl p-4 border border-[#374151]">
        <div className="animate-pulse flex items-center gap-2">
          <div className="h-4 w-4 bg-gray-700 rounded-full" />
          <div className="h-4 w-24 bg-gray-700 rounded" />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-[#111827] rounded-xl p-4 border border-red-500/50">
        <span className="text-red-400 text-sm">{error}</span>
      </div>
    )
  }

  const onlineCount = nodes.filter(n => n.status === 'online').length
  const totalCount = nodes.length

  return (
    <div className="bg-[#111827] rounded-xl border border-[#374151]">
      {/* Header */}
      <div className="p-4 border-b border-[#374151]">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold flex items-center gap-2">
            <Server className="w-4 h-4 text-purple-400" />
            BRAIN Swarm
          </h3>
          <div className="flex items-center gap-2 text-sm">
            <Circle 
              className={`w-2 h-2 ${onlineCount > 0 ? 'text-emerald-500' : 'text-red-500'}`} 
              fill="currentColor" 
            />
            <span className="text-gray-400">
              {onlineCount}/{totalCount} nodes
            </span>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      {stats && (
        <div className="p-4 grid grid-cols-2 gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-purple-500/10">
              <Activity className="w-4 h-4 text-purple-400" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Analyses</p>
              <p className="font-semibold">
                {stats.total_analyses.toLocaleString()}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-red-500/10">
              <Shield className="w-4 h-4 text-red-400" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Blocked</p>
              <p className="font-semibold">
                {stats.total_blocked.toLocaleString()}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-blue-500/10">
              <Server className="w-4 h-4 text-blue-400" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Patterns Shared</p>
              <p className="font-semibold">{stats.patterns_shared}</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-green-500/10">
              <Clock className="w-4 h-4 text-green-400" />
            </div>
            <div>
              <p className="text-xs text-gray-500">Avg Latency</p>
              <p className="font-semibold">{stats.avg_latency_ms}ms</p>
            </div>
          </div>
        </div>
      )}

      {/* Nodes List */}
      {nodes.length > 0 && (
        <div className="border-t border-[#374151]">
          <div className="p-3 space-y-2 max-h-48 overflow-y-auto">
            {nodes.map(node => (
              <div 
                key={node.node_id}
                className={`flex items-center justify-between p-2 rounded-lg ${statusBg[node.status]}`}
              >
                <div className="flex items-center gap-2">
                  <Circle 
                    className={`w-2 h-2 ${statusColors[node.status]}`} 
                    fill="currentColor" 
                  />
                  <span className="text-sm font-medium">{node.hostname}</span>
                  <span className="text-xs text-gray-500">:{node.port}</span>
                </div>
                <span className="text-xs text-gray-500">{node.version}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default SwarmStatus
