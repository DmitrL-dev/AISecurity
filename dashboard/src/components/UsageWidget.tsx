'use client'

/**
 * Usage Widget
 *
 * Displays tenant usage statistics with progress bars
 */

import { useState, useEffect } from 'react'
import { Activity, TrendingUp, Shield, Clock } from 'lucide-react'

interface UsageData {
  tenant: {
    id: string
    name: string
    plan: string
  }
  usage: {
    apiCalls: number
    analyses: number
    blockedThreats: number
  }
  limits: {
    analysesPerMonth: number
    remaining: number
  }
  period: {
    start: string
    end: string
  }
}

interface UsageWidgetProps {
  tenantId: string
}

export function UsageWidget({ tenantId }: UsageWidgetProps) {
  const [data, setData] = useState<UsageData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function fetchUsage() {
      try {
        const res = await fetch(`/api/tenants/${tenantId}/usage`)
        if (res.ok) {
          setData(await res.json())
        } else {
          setError('Failed to load usage')
        }
      } catch {
        setError('Failed to load usage')
      } finally {
        setLoading(false)
      }
    }

    fetchUsage()
  }, [tenantId])

  if (loading) {
    return (
      <div className="bg-[#111827] rounded-xl p-4 border border-[#374151] animate-pulse">
        <div className="h-4 w-24 bg-gray-700 rounded mb-4" />
        <div className="space-y-3">
          <div className="h-2 bg-gray-700 rounded" />
          <div className="h-2 bg-gray-700 rounded w-3/4" />
        </div>
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="bg-[#111827] rounded-xl p-4 border border-red-500/50">
        <span className="text-red-400 text-sm">{error}</span>
      </div>
    )
  }

  const usagePercent = Math.min(
    100,
    (data.usage.analyses / data.limits.analysesPerMonth) * 100
  )
  const isNearLimit = usagePercent > 80
  const isOverLimit = usagePercent >= 100

  return (
    <div className="bg-[#111827] rounded-xl border border-[#374151]">
      {/* Header */}
      <div className="p-4 border-b border-[#374151]">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold flex items-center gap-2">
            <Activity className="w-4 h-4 text-blue-400" />
            Usage
          </h3>
          <span className="text-xs text-gray-500 capitalize">
            {data.tenant.plan} plan
          </span>
        </div>
      </div>

      {/* Usage Bar */}
      <div className="p-4">
        <div className="mb-2 flex justify-between text-sm">
          <span className="text-gray-400">Analyses</span>
          <span className={isOverLimit ? 'text-red-400' : 'text-gray-300'}>
            {data.usage.analyses.toLocaleString()} /{' '}
            {data.limits.analysesPerMonth === Infinity
              ? '∞'
              : data.limits.analysesPerMonth.toLocaleString()}
          </span>
        </div>
        <div className="h-2 bg-gray-800 rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${
              isOverLimit
                ? 'bg-red-500'
                : isNearLimit
                ? 'bg-yellow-500'
                : 'bg-emerald-500'
            }`}
            style={{ width: `${Math.min(100, usagePercent)}%` }}
          />
        </div>
        <div className="mt-1 text-xs text-gray-500">
          {data.limits.remaining.toLocaleString()} remaining this month
        </div>
      </div>

      {/* Stats Grid */}
      <div className="px-4 pb-4 grid grid-cols-2 gap-3">
        <div className="flex items-center gap-2 p-2 rounded-lg bg-blue-500/10">
          <TrendingUp className="w-4 h-4 text-blue-400" />
          <div>
            <p className="text-xs text-gray-500">API Calls</p>
            <p className="font-semibold text-sm">
              {data.usage.apiCalls.toLocaleString()}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 p-2 rounded-lg bg-red-500/10">
          <Shield className="w-4 h-4 text-red-400" />
          <div>
            <p className="text-xs text-gray-500">Blocked</p>
            <p className="font-semibold text-sm">
              {data.usage.blockedThreats.toLocaleString()}
            </p>
          </div>
        </div>
      </div>

      {/* Period */}
      <div className="px-4 pb-4">
        <div className="flex items-center gap-1 text-xs text-gray-500">
          <Clock className="w-3 h-3" />
          Period: {data.period.start} → {data.period.end}
        </div>
      </div>
    </div>
  )
}

export default UsageWidget
