'use client'

import { useState, useRef } from 'react'
import { ChevronDown, Check, Zap } from 'lucide-react'

interface Engine {
  name: string
  enabled: boolean
}

interface EngineSelectorProps {
  engines: Engine[]
  selected: string[]
  onChange: (selected: string[]) => void
}

// Preset groups
const PRESETS = {
  all: { label: 'All Engines', filter: () => true },
  injection: { 
    label: 'Injection', 
    filter: (name: string) => 
      name.includes('injection') || 
      name.includes('prompt') || 
      name.includes('jailbreak') 
  },
  jailbreak: { 
    label: 'Jailbreak', 
    filter: (name: string) => 
      name.includes('jailbreak') || 
      name.includes('adversarial') ||
      name.includes('poetry')
  },
  pii: { 
    label: 'PII/Data', 
    filter: (name: string) => 
      name.includes('pii') || 
      name.includes('data') ||
      name.includes('leak')
  },
}

export default function EngineSelector({ engines, selected, onChange }: EngineSelectorProps) {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  const enabledEngines = engines.filter(e => e.enabled)
  const selectedCount = selected.length
  const totalCount = enabledEngines.length

  function toggleEngine(name: string) {
    if (selected.includes(name)) {
      onChange(selected.filter(s => s !== name))
    } else {
      onChange([...selected, name])
    }
  }

  function applyPreset(key: keyof typeof PRESETS) {
    if (key === 'all') {
      // Toggle: if all selected, deselect all; otherwise select all
      if (selected.length === enabledEngines.length) {
        onChange([])
      } else {
        onChange(enabledEngines.map(e => e.name))
      }
    } else {
      const preset = PRESETS[key]
      const matching = enabledEngines
        .filter(e => preset.filter(e.name))
        .map(e => e.name)
      // Add matching to selection
      const newSelected = [...new Set([...selected, ...matching])]
      onChange(newSelected)
    }
  }

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-4 py-2 bg-gray-800/50 border border-gray-700 rounded-lg text-sm text-gray-300 hover:border-purple-500/50 transition-colors"
      >
        <Zap className="w-4 h-4 text-purple-400" />
        <span>
          {selectedCount === 0 
            ? 'All Engines' 
            : selectedCount === totalCount 
              ? 'All Engines' 
              : `${selectedCount} Engines`}
        </span>
        <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute z-50 mt-2 w-72 bg-[#1a1f2e] border border-gray-700 rounded-xl shadow-xl overflow-hidden">
          {/* Presets */}
          <div className="p-2 border-b border-gray-700 flex flex-wrap gap-1">
            {Object.entries(PRESETS).map(([key, preset]) => (
              <button
                key={key}
                onClick={() => applyPreset(key as keyof typeof PRESETS)}
                className="px-2 py-1 text-xs bg-purple-500/20 text-purple-300 rounded hover:bg-purple-500/30 transition-colors"
              >
                {preset.label}
              </button>
            ))}
          </div>

          {/* Engine List */}
          <div className="max-h-64 overflow-y-auto">
            {enabledEngines.length === 0 ? (
              <div className="p-4 text-center text-gray-500 text-sm">
                No engines available
              </div>
            ) : (
              enabledEngines.map(engine => (
                <button
                  key={engine.name}
                  onClick={() => toggleEngine(engine.name)}
                  className="w-full flex items-center justify-between px-3 py-2 hover:bg-gray-800/50 transition-colors"
                >
                  <span className="text-sm text-gray-300 truncate">{engine.name}</span>
                  <div className={`w-5 h-5 rounded border flex items-center justify-center transition-colors ${
                    selected.includes(engine.name) 
                      ? 'bg-purple-500 border-purple-500' 
                      : 'border-gray-600'
                  }`}>
                    {selected.includes(engine.name) && (
                      <Check className="w-3 h-3 text-white" />
                    )}
                  </div>
                </button>
              ))
            )}
          </div>

          {/* Footer */}
          <div className="p-2 border-t border-gray-700 flex justify-between items-center">
            <span className="text-xs text-gray-500">
              {selectedCount} of {totalCount} selected
            </span>
            <button
              onClick={() => setIsOpen(false)}
              className="text-xs text-purple-400 hover:text-purple-300"
            >
              Done
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
