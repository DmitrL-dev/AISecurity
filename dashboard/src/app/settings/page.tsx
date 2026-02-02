'use client'

import { useState } from 'react'
import { 
  Settings, 
  Key, 
  Bell, 
  Moon, 
  Sun,
  Shield,
  Database,
  Globe,
  Save,
  Copy,
  Eye,
  EyeOff,
  Check
} from 'lucide-react'

export default function SettingsPage() {
  const [theme, setTheme] = useState<'dark' | 'light'>('dark')
  const [showApiKey, setShowApiKey] = useState(false)
  const [copied, setCopied] = useState(false)
  const [saved, setSaved] = useState(false)
  const [brainUrl, setBrainUrl] = useState('http://localhost:8000')
  const [auditLevel, setAuditLevel] = useState<'minimal' | 'standard' | 'detailed' | 'forensic'>('standard')
  const [notifications, setNotifications] = useState({
    critical: true,
    high: true,
    medium: false,
    email: true,
    slack: false,
  })
  const [engines, setEngines] = useState<Record<string, boolean>>({
    injection: true,
    jailbreak: true,
    pii: true,
    semantic: true,
    behavioral: true,
    rag_guard: false,
    mcp_security: false,
    tda_enhanced: false,
  })

  const apiKey = 'sk-sentinel-xxxx-xxxx-xxxx-xxxxxxxxxxxx'

  // Load settings from localStorage on mount
  useState(() => {
    if (typeof window !== 'undefined') {
      const savedSettings = localStorage.getItem('sentinel-settings')
      if (savedSettings) {
        try {
          const parsed = JSON.parse(savedSettings)
          if (parsed.brainUrl) setBrainUrl(parsed.brainUrl)
          if (parsed.auditLevel) setAuditLevel(parsed.auditLevel)
          if (parsed.notifications) setNotifications(parsed.notifications)
          if (parsed.engines) setEngines(parsed.engines)
          if (parsed.theme) setTheme(parsed.theme)
        } catch {}
      }
    }
  })

  const copyApiKey = () => {
    navigator.clipboard.writeText(apiKey)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const saveSettings = async () => {
    const settings = { brainUrl, auditLevel, notifications, engines, theme }
    localStorage.setItem('sentinel-settings', JSON.stringify(settings))
    
    // Also try to save audit level to BRAIN
    try {
      await fetch('/api/brain/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ audit_level: auditLevel }),
      })
    } catch {}
    
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const auditLevels = [
    { id: 'minimal', name: 'Minimal', desc: 'Only critical events' },
    { id: 'standard', name: 'Standard', desc: 'Security events + outcomes' },
    { id: 'detailed', name: 'Detailed', desc: 'Full analysis context' },
    { id: 'forensic', name: 'Forensic', desc: 'Complete payload logging' },
  ] as const

  const toggleEngine = (name: string) => {
    setEngines(prev => ({ ...prev, [name]: !prev[name] }))
  }

  return (
    <div className="max-w-4xl space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Settings className="w-7 h-7 text-gray-400" />
          Settings
        </h1>
        <p className="text-gray-400 text-sm">Configure SENTINEL dashboard preferences</p>
      </div>

      {/* BRAIN Connection */}
      <div className="card">
        <div className="card-header">
          <div className="flex items-center gap-3">
            <div className="icon-container icon-container--success">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h3 className="card-title">BRAIN Connection</h3>
              <p className="card-subtitle">API endpoint configuration</p>
            </div>
          </div>
        </div>
        <div className="card-content space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-2">API Endpoint</label>
            <input 
              type="text"
              value={brainUrl}
              onChange={e => setBrainUrl(e.target.value)}
              className="w-full px-4 py-2 bg-gray-900/50 rounded-lg border border-gray-700 focus:border-purple-500 focus:outline-none"
            />
          </div>
          
          <div className="flex items-center gap-2 text-sm">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            <span className="text-green-400">Connected</span>
            <span className="text-gray-500">• Version 1.7.0</span>
          </div>
        </div>
      </div>

      {/* Audit Level */}
      <div className="card">
        <div className="card-header">
          <div className="flex items-center gap-3">
            <div className="icon-container icon-container--warning">
              <Shield className="w-5 h-5" />
            </div>
            <div>
              <h3 className="card-title">Audit Level</h3>
              <p className="card-subtitle">Controls logging detail and data retention</p>
            </div>
          </div>
        </div>
        <div className="card-content">
          <div className="grid grid-cols-2 gap-3">
            {auditLevels.map(level => (
              <button
                key={level.id}
                onClick={() => setAuditLevel(level.id)}
                className={`p-4 rounded-xl border text-left transition-all ${
                  auditLevel === level.id
                    ? 'border-purple-500 bg-purple-500/10'
                    : 'border-gray-700 hover:border-gray-600'
                }`}
              >
                <p className="font-medium">{level.name}</p>
                <p className="text-xs text-gray-400 mt-1">{level.desc}</p>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Engine Configuration */}
      <div className="card">
        <div className="card-header">
          <div className="flex items-center gap-3">
            <div className="icon-container icon-container--info">
              <Globe className="w-5 h-5" />
            </div>
            <div>
              <h3 className="card-title">Default Engines</h3>
              <p className="card-subtitle">Enable/disable engines for analysis</p>
            </div>
          </div>
        </div>
        <div className="card-content">
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(engines).map(([name, enabled]) => (
              <button
                key={name}
                onClick={() => toggleEngine(name)}
                className={`flex items-center justify-between p-3 rounded-lg border transition-all ${
                  enabled
                    ? 'border-green-500/50 bg-green-500/10'
                    : 'border-gray-700 bg-gray-900/30'
                }`}
              >
                <span className="text-sm">{name}</span>
                <span className={`w-2 h-2 rounded-full ${enabled ? 'bg-green-400' : 'bg-gray-600'}`} />
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* API Keys */}
      <div className="card">
        <div className="card-header">
          <div className="flex items-center gap-3">
            <div className="icon-container icon-container--primary">
              <Key className="w-5 h-5" />
            </div>
            <div>
              <h3 className="card-title">API Keys</h3>
              <p className="card-subtitle">Manage authentication tokens</p>
            </div>
          </div>
        </div>
        <div className="card-content space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-2">SENTINEL API Key</label>
            <div className="flex gap-2">
              <div className="flex-1 flex items-center bg-gray-900/50 rounded-lg border border-gray-700 px-4 py-2">
                <code className="flex-1 text-sm font-mono">
                  {showApiKey ? apiKey : '••••••••••••••••••••••••••••••••'}
                </code>
                <button 
                  onClick={() => setShowApiKey(!showApiKey)}
                  className="p-1 hover:bg-white/10 rounded"
                >
                  {showApiKey ? <EyeOff className="w-4 h-4 text-gray-400" /> : <Eye className="w-4 h-4 text-gray-400" />}
                </button>
              </div>
              <button 
                onClick={copyApiKey}
                className="px-4 py-2 bg-purple-500/20 text-purple-400 rounded-lg hover:bg-purple-500/30 transition-colors flex items-center gap-2"
              >
                {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                {copied ? 'Copied!' : 'Copy'}
              </button>
            </div>
          </div>
          
          <button className="px-4 py-2 border border-gray-700 rounded-lg hover:border-purple-500 transition-colors text-sm">
            Generate New Key
          </button>
        </div>
      </div>

      {/* Notifications */}
      <div className="card">
        <div className="card-header">
          <div className="flex items-center gap-3">
            <div className="icon-container icon-container--secondary">
              <Bell className="w-5 h-5" />
            </div>
            <div>
              <h3 className="card-title">Notifications</h3>
              <p className="card-subtitle">Alert preferences</p>
            </div>
          </div>
        </div>
        <div className="card-content space-y-3">
          {[
            { key: 'critical', label: 'Critical Alerts', desc: 'Immediate notification for critical threats' },
            { key: 'high', label: 'High Severity', desc: 'Alert for high severity incidents' },
            { key: 'email', label: 'Email Notifications', desc: 'Send alerts to your email' },
          ].map(item => (
            <div key={item.key} className="flex items-center justify-between py-2">
              <div>
                <p className="font-medium text-sm">{item.label}</p>
                <p className="text-xs text-gray-500">{item.desc}</p>
              </div>
              <button 
                onClick={() => setNotifications({...notifications, [item.key]: !notifications[item.key as keyof typeof notifications]})}
                className={`w-11 h-6 rounded-full transition-colors ${notifications[item.key as keyof typeof notifications] ? 'bg-purple-500' : 'bg-gray-600'}`}
              >
                <span className={`block w-5 h-5 bg-white rounded-full transition-transform ${notifications[item.key as keyof typeof notifications] ? 'translate-x-5' : 'translate-x-0.5'}`} />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Appearance */}
      <div className="card">
        <div className="card-header">
          <div className="flex items-center gap-3">
            <div className="icon-container" style={{ background: 'rgba(234, 179, 8, 0.2)' }}>
              <Moon className="w-5 h-5 text-yellow-400" />
            </div>
            <div>
              <h3 className="card-title">Appearance</h3>
              <p className="card-subtitle">Theme preference</p>
            </div>
          </div>
        </div>
        <div className="card-content">
          <div className="flex gap-4">
            <button 
              onClick={() => setTheme('dark')}
              className={`flex-1 p-4 rounded-lg border transition-all ${
                theme === 'dark' 
                  ? 'border-purple-500 bg-purple-500/10' 
                  : 'border-gray-700 hover:border-gray-600'
              }`}
            >
              <Moon className="w-6 h-6 mx-auto mb-2" />
              <p className="font-medium text-sm">Dark</p>
            </button>
            <button 
              onClick={() => setTheme('light')}
              className={`flex-1 p-4 rounded-lg border transition-all ${
                theme === 'light' 
                  ? 'border-purple-500 bg-purple-500/10' 
                  : 'border-gray-700 hover:border-gray-600'
              }`}
            >
              <Sun className="w-6 h-6 mx-auto mb-2" />
              <p className="font-medium text-sm">Light</p>
            </button>
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex justify-end">
        <button 
          onClick={saveSettings}
          className={`flex items-center gap-2 px-6 py-2.5 rounded-lg transition-all ${
            saved 
              ? 'bg-green-500 text-white' 
              : 'bg-purple-500 hover:bg-purple-600 text-white'
          }`}
        >
          {saved ? <Check className="w-4 h-4" /> : <Save className="w-4 h-4" />}
          {saved ? 'Saved!' : 'Save Changes'}
        </button>
      </div>
    </div>
  )
}
