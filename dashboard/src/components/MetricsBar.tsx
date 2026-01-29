'use client'

import { Database, Shield, Cpu, Activity, TrendingUp, TrendingDown, Loader2 } from 'lucide-react'
import { useDashboardMetrics, useBrainHealth } from '@/lib/hooks'

interface MetricCardProps {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: string | number
  trend?: { value: number; positive: boolean }
  accentColor: string
  glowColor: string
  loading?: boolean
}

function MetricCard({ icon: Icon, label, value, trend, accentColor, glowColor, loading }: MetricCardProps) {
  return (
    <div 
      className={`
        relative overflow-hidden
        bg-gradient-to-br from-[#1a1f2e] to-[#151922]
        rounded-xl border border-[#374151] p-3 lg:p-4
        hover:border-purple-500/50 transition-all duration-300
        hover:shadow-lg group
      `}
      style={{ '--glow-color': glowColor } as React.CSSProperties}
    >
      {/* Background glow on hover */}
      <div 
        className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500"
        style={{ 
          background: `radial-gradient(circle at 100% 0%, ${glowColor}15 0%, transparent 50%)` 
        }}
      />
      
      <div className="relative flex items-start justify-between">
        <div className="min-w-0 flex-1">
          <p className="text-gray-400 text-xs lg:text-sm mb-1 truncate">{label}</p>
          {loading ? (
            <Loader2 className="w-5 h-5 lg:w-6 lg:h-6 animate-spin text-gray-400" />
          ) : (
            <p className="text-xl lg:text-2xl font-bold tracking-tight">
              {typeof value === 'number' ? value.toLocaleString() : value}
            </p>
          )}
          {trend && !loading && (
            <div className={`flex items-center gap-1 mt-1 text-xs lg:text-sm ${trend.positive ? 'text-emerald-400' : 'text-red-400'}`}>
              {trend.positive ? (
                <TrendingUp className="w-3 h-3" />
              ) : (
                <TrendingDown className="w-3 h-3" />
              )}
              <span>{trend.positive ? '+' : ''}{trend.value}%</span>
            </div>
          )}
        </div>
        <div className={`p-2 lg:p-2.5 rounded-lg ${accentColor} transition-transform duration-300 group-hover:scale-110 flex-shrink-0`}>
          <Icon className="w-4 h-4 lg:w-5 lg:h-5" />
        </div>
      </div>
      
      {/* Sparkline - hidden on mobile */}
      <div className="hidden sm:flex mt-3 h-8 items-end gap-0.5">
        {[40, 60, 45, 80, 55, 70, 90, 65, 75, 85].map((h, i) => (
          <div 
            key={i}
            className="flex-1 bg-white/10 rounded-t transition-all duration-300"
            style={{ height: `${h}%`, transitionDelay: `${i * 50}ms` }}
          />
        ))}
      </div>
    </div>
  )
}

export function MetricsBar() {
  const metrics = useDashboardMetrics();
  const { loading } = useBrainHealth();

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 lg:gap-4 mb-4 lg:mb-6">
      <MetricCard
        icon={Database}
        label="Payloads"
        value={metrics.payloads}
        trend={{ value: 12, positive: true }}
        accentColor="bg-purple-500/20 text-purple-400"
        glowColor="#8b5cf6"
        loading={loading}
      />
      <MetricCard
        icon={Shield}
        label="Threats Blocked"
        value={metrics.threatsBlocked}
        trend={{ value: 8, positive: false }}
        accentColor="bg-red-500/20 text-red-400"
        glowColor="#ef4444"
        loading={loading}
      />
      <MetricCard
        icon={Cpu}
        label="Active Engines"
        value={metrics.activeEngines}
        accentColor="bg-emerald-500/20 text-emerald-400"
        glowColor="#22c55e"
        loading={loading}
      />
      <MetricCard
        icon={Activity}
        label="API Calls"
        value={metrics.apiCalls}
        trend={{ value: 23, positive: true }}
        accentColor="bg-cyan-500/20 text-cyan-400"
        glowColor="#06b6d4"
        loading={loading}
      />
    </div>
  )
}
