'use client'

import { Search, Bell, Calendar, Globe, Circle, Menu } from 'lucide-react'
import { useState } from 'react'
import { useBrainHealth } from '@/lib/hooks'
import { useSidebar } from '@/components/Sidebar'
import { UserMenu } from '@/components/auth'

export function Header() {
  const [timeRange, _setTimeRange] = useState('Past 7 Days')
  const { health, loading } = useBrainHealth()
  const { setMobileOpen } = useSidebar()

  const statusColor = {
    healthy: 'bg-emerald-500',
    degraded: 'bg-yellow-500',
    unhealthy: 'bg-red-500',
    unknown: 'bg-gray-500',
  }

  const currentStatus = health?.status || 'unknown'

  return (
    <header className="h-14 lg:h-16 bg-[#111827] border-b border-[#374151] flex items-center justify-between px-4 lg:px-6">
      {/* Left: Mobile menu + Title + BRAIN Status */}
      <div className="flex items-center gap-3 lg:gap-4">
        {/* Mobile menu button */}
        <button 
          onClick={() => setMobileOpen(true)}
          className="lg:hidden p-2 -ml-2 hover:bg-white/10 rounded-lg"
        >
          <Menu className="w-5 h-5" />
        </button>
        
        <h1 className="text-lg lg:text-xl font-semibold">Dashboard</h1>
        
        {/* BRAIN Status Indicator (hidden on small screens) */}
        <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-[#1a1f2e] rounded-full border border-[#374151]">
          <Circle 
            className={`w-2 h-2 ${statusColor[currentStatus]} ${!loading && currentStatus === 'healthy' ? 'animate-pulse' : ''}`}
            fill="currentColor"
          />
          <span className="text-xs text-gray-400">
            BRAIN {health?.version || 'v?.?.?'}
          </span>
        </div>
      </div>

      {/* Center: Filters (hidden on mobile) */}
      <div className="hidden md:flex items-center gap-3">
        {/* Time Range */}
        <button className="flex items-center gap-2 px-3 py-2 bg-[#1a1f2e] rounded-lg border border-[#374151] hover:border-purple-500 transition-colors">
          <Calendar className="w-4 h-4 text-gray-400" />
          <span className="text-sm">{timeRange}</span>
          <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </button>

        {/* Global */}
        <button className="flex items-center gap-2 px-3 py-2 bg-[#1a1f2e] rounded-lg border border-[#374151] hover:border-purple-500 transition-colors">
          <Globe className="w-4 h-4 text-gray-400" />
          <span className="text-sm">Global</span>
        </button>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search..."
            className="pl-10 pr-4 py-2 bg-[#1a1f2e] rounded-lg border border-[#374151] focus:border-purple-500 focus:outline-none text-sm w-48 lg:w-64 transition-colors"
          />
        </div>
      </div>

      {/* Right: Notifications + User */}
      <div className="flex items-center gap-2 lg:gap-4">
        {/* Search button (mobile only) */}
        <button className="md:hidden p-2 rounded-lg hover:bg-[#1a1f2e] transition-colors">
          <Search className="w-5 h-5 text-gray-400" />
        </button>
        
        <button className="relative p-2 rounded-lg hover:bg-[#1a1f2e] transition-colors">
          <Bell className="w-5 h-5 text-gray-400" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
        </button>
        
        <div className="hidden sm:flex items-center pl-2 lg:pl-4 border-l border-[#374151]">
          <UserMenu />
        </div>
      </div>
    </header>
  )
}
