'use client'

/**
 * Engine Card
 *
 * Status card for AI Security engine with metrics
 */

import { useState, useEffect } from 'react'
import {
  Brain,
  Clock,
  CheckCircle,
  XCircle,
  Loader2,
  Settings,
  TrendingUp,
  AlertTriangle,
} from 'lucide-react'

interface EngineMetrics {
  call_count: number
  error_count: number
  avg_latency_ms: number
  [key: string]: unknown
}

interface EngineStats {
  engine: string
  status: 'healthy' | 'loading' | 'error' | 'offline'
  mode: string
  model: string
  metrics: EngineMetrics
}

interface EngineCardProps {
  name: string
  displayName: string
  description: string
  onConfigure?: () => void
  onSelect?: () => void
  selected?: boolean
}

const statusConfig = {
  healthy: {
    icon: CheckCircle,
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/20',
    border: 'border-emerald-500/30',
  },
  loading: {
    icon: Loader2,
    color: 'text-blue-400',
    bg: 'bg-blue-500/20',
    border: 'border-blue-500/30',
  },
  error: {
    icon: XCircle,
    color: 'text-red-400',
    bg: 'bg-red-500/20',
    border: 'border-red-500/30',
  },
  offline: {
    icon: AlertTriangle,
    color: 'text-gray-400',
    bg: 'bg-gray-500/20',
    border: 'border-gray-500/30',
  },
}

export function EngineCard({
  name,
  displayName,
  description,
  onConfigure,
  onSelect,
  selected = false,
}: EngineCardProps) {
  const [stats, setStats] = useState<EngineStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [_error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchStats() {
      try {
        const res = await fetch(`/api/brain/engines/${name}/stats`)
        if (res.ok) {
          setStats(await res.json())
        } else {
          setError('Failed to load')
        }
      } catch {
        setError('Connection failed')
      } finally {
        setLoading(false)
      }
    }

    fetchStats()
    const interval = setInterval(fetchStats, 30000) // Refresh every 30s
    return () => clearInterval(interval)
  }, [name])

  if (loading) {
    return (
      <div className="bg-[#111827] rounded-xl p-4 border border-[#374151] animate-pulse">
        <div className="h-6 w-32 bg-gray-700 rounded mb-2" />
        <div className="h-4 w-48 bg-gray-700 rounded mb-4" />
        <div className="grid grid-cols-3 gap-2">
          <div className="h-12 bg-gray-700 rounded" />
          <div className="h-12 bg-gray-700 rounded" />
          <div className="h-12 bg-gray-700 rounded" />
        </div>
      </div>
    )
  }

  const status = stats?.status || 'offline'
  const config = statusConfig[status]
  const StatusIcon = config.icon

  return (
    <div
      onClick={onSelect}
      className={`
        bg-[#111827] rounded-xl border transition-all cursor-pointer
        ${selected ? 'border-purple-500 ring-2 ring-purple-500/30' : 'border-[#374151] hover:border-[#4b5563]'}
      `}
    >
      {/* Header */}
      <div className="p-4 border-b border-[#374151]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${config.bg}`}>
              <Brain className={`w-5 h-5 ${config.color}`} />
            </div>
            <div>
              <h3 className="font-semibold flex items-center gap-2">
                {displayName}
                <StatusIcon
                  className={`w-4 h-4 ${config.color} ${status === 'loading' ? 'animate-spin' : ''}`}
                />
              </h3>
              <p className="text-xs text-gray-500">{description}</p>
            </div>
          </div>
          {onConfigure && (
            <button
              onClick={(e) => {
                e.stopPropagation()
                onConfigure()
              }}
              className="p-2 rounded-lg hover:bg-[#374151] transition-colors"
            >
              <Settings className="w-4 h-4 text-gray-400" />
            </button>
          )}
        </div>
      </div>

      {/* Metrics */}
      <div className="p-4 grid grid-cols-3 gap-3">
        <div className="text-center">
          <div className="flex items-center justify-center gap-1 text-blue-400">
            <TrendingUp className="w-3 h-3" />
            <span className="text-lg font-bold">
              {stats?.metrics.call_count?.toLocaleString() || 0}
            </span>
          </div>
          <p className="text-xs text-gray-500">Calls</p>
        </div>

        <div className="text-center">
          <div className="flex items-center justify-center gap-1 text-yellow-400">
            <Clock className="w-3 h-3" />
            <span className="text-lg font-bold">
              {stats?.metrics.avg_latency_ms?.toFixed(0) || 0}ms
            </span>
          </div>
          <p className="text-xs text-gray-500">Latency</p>
        </div>

        <div className="text-center">
          <div className="flex items-center justify-center gap-1 text-red-400">
            <XCircle className="w-3 h-3" />
            <span className="text-lg font-bold">
              {stats?.metrics.error_count || 0}
            </span>
          </div>
          <p className="text-xs text-gray-500">Errors</p>
        </div>
      </div>

      {/* Footer */}
      <div className="px-4 pb-3">
        <div className="flex items-center justify-between text-xs text-gray-500">
          <span className="truncate max-w-[60%]">{stats?.model}</span>
          <span className="capitalize">{stats?.mode}</span>
        </div>
      </div>
    </div>
  )
}

export default EngineCard
