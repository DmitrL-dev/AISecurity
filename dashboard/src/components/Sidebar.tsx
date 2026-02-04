'use client'

import { useState, createContext, useContext } from 'react'
import { 
  LayoutDashboard, 
  Shield, 
  ShieldCheck,
  Brain, 
  Crosshair, 
  GraduationCap, 
  Settings,
  ChevronLeft,
  ChevronRight,
  Menu,
  X,
  FileText,
  Search
} from 'lucide-react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

const navItems = [
  { icon: LayoutDashboard, label: 'Overview', href: '/' },
  { icon: Search, label: 'Analyze', href: '/analyze' },
  { icon: Shield, label: 'Incidents', href: '/incidents' },
  { icon: Brain, label: 'BRAIN', href: '/brain' },
  { icon: Crosshair, label: 'STRIKE', href: '/strike' },
  { icon: ShieldCheck, label: 'SHIELD', href: '/shield' },
  { icon: FileText, label: 'Audit Log', href: '/audit' },
  { icon: GraduationCap, label: 'Academy', href: '/academy' },
  { icon: Settings, label: 'Settings', href: '/settings' },
]


// Context for mobile sidebar state
export const SidebarContext = createContext<{
  mobileOpen: boolean
  setMobileOpen: (open: boolean) => void
}>({ mobileOpen: false, setMobileOpen: () => {} })

export function useSidebar() {
  return useContext(SidebarContext)
}

export function SidebarProvider({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false)
  return (
    <SidebarContext.Provider value={{ mobileOpen, setMobileOpen }}>
      {children}
    </SidebarContext.Provider>
  )
}

// Mobile menu button for header
export function MobileMenuButton() {
  const { setMobileOpen } = useSidebar()
  return (
    <button 
      onClick={() => setMobileOpen(true)}
      className="lg:hidden p-2 hover:bg-white/10 rounded-lg"
    >
      <Menu className="w-5 h-5" />
    </button>
  )
}

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)
  const { mobileOpen, setMobileOpen } = useSidebar()
  const pathname = usePathname()

  const sidebarContent = (
    <>
      {/* Logo */}
      <div className="h-16 flex items-center px-3 border-b border-[#374151]">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-cyan-500 rounded-xl flex items-center justify-center shadow-lg shadow-purple-500/25 flex-shrink-0">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <span className={`font-bold text-lg tracking-tight transition-opacity duration-200 ${collapsed ? 'lg:opacity-0 lg:w-0' : 'opacity-100'}`}>
            SENTINEL
          </span>
        </div>
        {/* Mobile close button */}
        <button 
          onClick={() => setMobileOpen(false)}
          className="lg:hidden ml-auto p-2 hover:bg-white/10 rounded-lg"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-2 space-y-1">
        {navItems.map((item) => {
          const isActive = pathname === item.href
          return (
            <Link
              key={item.label}
              href={item.href}
              onClick={() => setMobileOpen(false)}
              className={`
                flex items-center gap-3 px-3 py-2.5 rounded-lg
                transition-all duration-200 group relative
                ${isActive 
                  ? 'bg-gradient-to-r from-purple-500/20 to-transparent text-white' 
                  : 'text-gray-400 hover:bg-white/5 hover:text-white'
                }
              `}
            >
              {/* Active indicator */}
              {isActive && (
                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-purple-500 rounded-r-full" />
              )}
              
              <item.icon className={`w-5 h-5 flex-shrink-0 transition-colors ${isActive ? 'text-purple-400' : 'group-hover:text-purple-400'}`} />
              
              <span className={`font-medium transition-opacity duration-200 ${collapsed ? 'lg:opacity-0 lg:w-0' : 'opacity-100'}`}>
                {item.label}
              </span>
              
              {/* Tooltip on collapsed (desktop only) */}
              {collapsed && (
                <div className="hidden lg:block absolute left-full ml-2 px-2 py-1 bg-[#1a1f2e] text-white text-sm rounded opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50 whitespace-nowrap border border-[#374151]">
                  {item.label}
                </div>
              )}
            </Link>
          )
        })}
      </nav>

      {/* Collapse button (desktop only) */}
      <button 
        onClick={() => setCollapsed(!collapsed)}
        className="hidden lg:flex absolute -right-3 top-20 w-6 h-6 bg-[#1a1f2e] border border-[#374151] rounded-full items-center justify-center hover:bg-purple-500 hover:border-purple-500 transition-all shadow-lg"
      >
        {collapsed ? (
          <ChevronRight className="w-3 h-3" />
        ) : (
          <ChevronLeft className="w-3 h-3" />
        )}
      </button>
      
      {/* Version */}
      <div className={`p-4 border-t border-[#374151] text-xs text-gray-500 ${collapsed ? 'lg:text-center' : ''}`}>
        {collapsed ? 'v2' : 'v2.0.0-beta'}
      </div>
    </>
  )

  return (
    <>
      {/* Mobile overlay */}
      {mobileOpen && (
        <div 
          className="lg:hidden fixed inset-0 bg-black/50 z-40"
          onClick={() => setMobileOpen(false)}
        />
      )}
      
      {/* Mobile sidebar */}
      <aside className={`
        lg:hidden fixed inset-y-0 left-0 z-50 w-64 bg-[#111827] border-r border-[#374151]
        flex flex-col transition-transform duration-300
        ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        {sidebarContent}
      </aside>
      
      {/* Desktop sidebar */}
      <aside className={`
        hidden lg:flex
        ${collapsed ? 'w-16' : 'w-56'} 
        bg-[#111827] border-r border-[#374151] 
        flex-col transition-all duration-300 ease-in-out
        relative
      `}>
        {sidebarContent}
      </aside>
    </>
  )
}
