'use client'

/**
 * Tenant Selector
 *
 * Dropdown to switch between tenants
 */

import { useState, useEffect } from 'react'
import { ChevronDown, Building2, Check } from 'lucide-react'

interface Tenant {
  id: string
  name: string
  slug: string
  plan: string
  role: string
}

interface TenantSelectorProps {
  currentTenantId?: string
  onSelect: (tenantId: string) => void
}

export function TenantSelector({ currentTenantId, onSelect }: TenantSelectorProps) {
  const [tenants, setTenants] = useState<Tenant[]>([])
  const [isOpen, setIsOpen] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function fetchTenants() {
      try {
        const res = await fetch('/api/tenants')
        if (res.ok) {
          const data = await res.json()
          setTenants(data.tenants || [])
        }
      } catch (err) {
        console.error('Failed to fetch tenants:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchTenants()
  }, [])

  const currentTenant = tenants.find(t => t.id === currentTenantId) || tenants[0]

  if (loading) {
    return (
      <div className="h-9 w-40 bg-gray-800 rounded-lg animate-pulse" />
    )
  }

  if (tenants.length === 0) {
    return null
  }

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 rounded-lg bg-[#1f2937] 
                   border border-[#374151] hover:border-[#4b5563] transition-colors"
      >
        <Building2 className="w-4 h-4 text-purple-400" />
        <span className="text-sm font-medium truncate max-w-[120px]">
          {currentTenant?.name || 'Select Tenant'}
        </span>
        <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute top-full mt-1 left-0 z-50 w-56 bg-[#1f2937] 
                          border border-[#374151] rounded-lg shadow-xl overflow-hidden">
            {tenants.map(tenant => (
              <button
                key={tenant.id}
                onClick={() => {
                  onSelect(tenant.id)
                  setIsOpen(false)
                }}
                className={`w-full flex items-center gap-3 px-3 py-2 text-left 
                           hover:bg-[#374151] transition-colors ${
                             tenant.id === currentTenantId ? 'bg-[#374151]' : ''
                           }`}
              >
                <Building2 className="w-4 h-4 text-gray-400" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{tenant.name}</p>
                  <p className="text-xs text-gray-500 capitalize">
                    {tenant.plan} • {tenant.role}
                  </p>
                </div>
                {tenant.id === currentTenantId && (
                  <Check className="w-4 h-4 text-emerald-400" />
                )}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

export default TenantSelector
