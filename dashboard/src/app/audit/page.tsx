'use client'

import { useState, useEffect } from 'react'
import { 
  Shield, 
  RefreshCw, 
  AlertTriangle, 
  Info, 
  AlertCircle,
  Bug,
  Filter,
  Clock,
  User,
  Activity,
  Download
} from 'lucide-react'

interface AuditEntry {
  timestamp: string
  level: string
  event_type: string
  actor: string
  resource: string
  action: string
  details: Record<string, any>
  outcome: string
  sequence: number
}

const LEVEL_COLORS: Record<string, string> = {
  CRITICAL: 'bg-red-500/20 text-red-400 border-red-500/50',
  WARNING: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/50',
  INFO: 'bg-blue-500/20 text-blue-400 border-blue-500/50',
  DEBUG: 'bg-gray-500/20 text-gray-400 border-gray-500/50',
}

const LEVEL_ICONS: Record<string, typeof AlertTriangle> = {
  CRITICAL: AlertCircle,
  WARNING: AlertTriangle,
  INFO: Info,
  DEBUG: Bug,
}

export default function AuditPage() {
  const [entries, setEntries] = useState<AuditEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [levelFilter, setLevelFilter] = useState<string>('all')
  const [refreshing, setRefreshing] = useState(false)
  const [exporting, setExporting] = useState(false)

  async function fetchLogs() {
    try {
      setRefreshing(true)
      const params = new URLSearchParams({ limit: '100' })
      if (levelFilter !== 'all') params.set('level', levelFilter)
      
      const res = await fetch(`/api/brain/audit/logs?${params}`)
      if (!res.ok) throw new Error('Failed to fetch audit logs')
      
      const data = await res.json()
      setEntries(data.entries || [])
      setError(null)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  async function handleExport(format: 'json' | 'csv') {
    try {
      setExporting(true)
      
      // Request export token
      const res = await fetch('/api/brain/audit/export', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          format,
          limit: 1000,
          level: levelFilter !== 'all' ? levelFilter : undefined,
        }),
      })
      
      if (!res.ok) throw new Error('Failed to create export')
      
      const data = await res.json()
      
      // Download via the secure token URL
      window.location.href = `/api/brain/audit/download/${data.token}`
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setExporting(false)
    }
  }

  useEffect(() => {
    fetchLogs()
    const interval = setInterval(fetchLogs, 30000) // Refresh every 30s
    return () => clearInterval(interval)
  }, [levelFilter])

  const formatTime = (iso: string) => {
    try {
      return new Date(iso).toLocaleString()
    } catch {
      return iso
    }
  }

  return (
    <div className="min-h-screen bg-[#0d1117] text-white p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-4">
          <div className="p-3 rounded-xl bg-gradient-to-br from-purple-500/20 to-blue-500/20 border border-purple-500/30">
            <Shield className="w-8 h-8 text-purple-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">
              Audit Log
            </h1>
            <p className="text-gray-400">System security events and changes</p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          {/* Level Filter */}
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-400" />
            <select
              value={levelFilter}
              onChange={(e) => setLevelFilter(e.target.value)}
              className="bg-[#1a1f2e] border border-[#374151] rounded-lg px-3 py-2 text-sm focus:border-purple-500 focus:outline-none"
            >
              <option value="all">All Levels</option>
              <option value="CRITICAL">Critical</option>
              <option value="WARNING">Warning</option>
              <option value="INFO">Info</option>
              <option value="DEBUG">Debug</option>
            </select>
          </div>

          {/* Export Dropdown */}
          <div className="relative group">
            <button
              disabled={exporting}
              className="flex items-center gap-2 px-4 py-2 bg-green-500/20 text-green-400 rounded-lg hover:bg-green-500/30 transition-colors disabled:opacity-50"
            >
              <Download className={`w-4 h-4 ${exporting ? 'animate-bounce' : ''}`} />
              Export
            </button>
            <div className="absolute right-0 top-full mt-1 bg-[#1a1f2e] border border-[#374151] rounded-lg shadow-lg opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-10">
              <button
                onClick={() => handleExport('json')}
                className="block w-full px-4 py-2 text-left text-sm text-gray-300 hover:bg-[#252b3b] rounded-t-lg"
              >
                Export as JSON
              </button>
              <button
                onClick={() => handleExport('csv')}
                className="block w-full px-4 py-2 text-left text-sm text-gray-300 hover:bg-[#252b3b] rounded-b-lg"
              >
                Export as CSV
              </button>
            </div>
          </div>

          {/* Refresh Button */}
          <button
            onClick={fetchLogs}
            disabled={refreshing}
            className="flex items-center gap-2 px-4 py-2 bg-purple-500/20 text-purple-400 rounded-lg hover:bg-purple-500/30 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        {['CRITICAL', 'WARNING', 'INFO', 'DEBUG'].map(level => {
          const count = entries.filter(e => e.level === level).length
          const Icon = LEVEL_ICONS[level]
          return (
            <div 
              key={level}
              className={`p-4 rounded-xl border ${LEVEL_COLORS[level]}`}
            >
              <div className="flex items-center justify-between">
                <span className="font-medium">{level}</span>
                <Icon className="w-5 h-5" />
              </div>
              <div className="text-2xl font-bold mt-2">{count}</div>
            </div>
          )
        })}
      </div>

      {/* Error */}
      {error && (
        <div className="mb-6 p-4 bg-red-500/20 border border-red-500/50 rounded-lg text-red-400">
          {error}
        </div>
      )}

      {/* Table */}
      <div className="bg-[#1a1f2e] rounded-xl border border-[#374151] overflow-hidden">
        <table className="w-full">
          <thead>
            <tr className="border-b border-[#374151] text-left text-gray-400">
              <th className="px-4 py-3 font-medium">Time</th>
              <th className="px-4 py-3 font-medium">Level</th>
              <th className="px-4 py-3 font-medium">Event</th>
              <th className="px-4 py-3 font-medium">Actor</th>
              <th className="px-4 py-3 font-medium">Resource</th>
              <th className="px-4 py-3 font-medium">Action</th>
              <th className="px-4 py-3 font-medium">Outcome</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} className="text-center py-8 text-gray-400">
                  <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" />
                  Loading audit logs...
                </td>
              </tr>
            ) : entries.length === 0 ? (
              <tr>
                <td colSpan={7} className="text-center py-8 text-gray-400">
                  <Activity className="w-6 h-6 mx-auto mb-2" />
                  No audit entries found
                </td>
              </tr>
            ) : (
              entries.map((entry, i) => {
                const Icon = LEVEL_ICONS[entry.level] || Info
                return (
                  <tr 
                    key={entry.sequence || i}
                    className="border-b border-[#374151]/50 hover:bg-[#252b3b] transition-colors"
                  >
                    <td className="px-4 py-3 text-sm">
                      <div className="flex items-center gap-2 text-gray-400">
                        <Clock className="w-3 h-3" />
                        {formatTime(entry.timestamp)}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium border ${LEVEL_COLORS[entry.level] || LEVEL_COLORS.INFO}`}>
                        <Icon className="w-3 h-3" />
                        {entry.level}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm font-mono text-purple-400">
                      {entry.event_type}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <div className="flex items-center gap-2">
                        <User className="w-3 h-3 text-gray-400" />
                        {entry.actor}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-300">
                      {entry.resource}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-300">
                      {entry.action}
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <span className={`px-2 py-1 rounded text-xs ${
                        entry.outcome === 'success' 
                          ? 'bg-green-500/20 text-green-400' 
                          : 'bg-red-500/20 text-red-400'
                      }`}>
                        {entry.outcome}
                      </span>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Footer info */}
      <div className="mt-4 text-sm text-gray-500 flex items-center justify-between">
        <span>Showing {entries.length} entries</span>
        <span>Auto-refresh every 30 seconds</span>
      </div>
    </div>
  )
}
