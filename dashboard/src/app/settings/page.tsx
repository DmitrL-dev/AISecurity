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
  const [notifications, setNotifications] = useState({
    critical: true,
    high: true,
    medium: false,
    email: true,
    slack: false,
  })

  const apiKey = 'sk-sentinel-xxxx-xxxx-xxxx-xxxxxxxxxxxx'

  const copyApiKey = () => {
    navigator.clipboard.writeText(apiKey)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
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

      {/* API Keys */}
      <div className="bg-[#1a1f2e] rounded-xl border border-[#374151] p-6">
        <h2 className="text-lg font-semibold flex items-center gap-2 mb-4">
          <Key className="w-5 h-5 text-purple-400" />
          API Keys
        </h2>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-2">SENTINEL API Key</label>
            <div className="flex gap-2">
              <div className="flex-1 flex items-center bg-[#111827] rounded-lg border border-[#374151] px-4 py-2">
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
          
          <button className="px-4 py-2 border border-[#374151] rounded-lg hover:border-purple-500 transition-colors text-sm">
            Generate New Key
          </button>
        </div>
      </div>

      {/* Notifications */}
      <div className="bg-[#1a1f2e] rounded-xl border border-[#374151] p-6">
        <h2 className="text-lg font-semibold flex items-center gap-2 mb-4">
          <Bell className="w-5 h-5 text-cyan-400" />
          Notifications
        </h2>
        
        <div className="space-y-4">
          <div className="flex items-center justify-between py-2">
            <div>
              <p className="font-medium">Critical Alerts</p>
              <p className="text-sm text-gray-400">Immediate notification for critical threats</p>
            </div>
            <button 
              onClick={() => setNotifications({...notifications, critical: !notifications.critical})}
              className={`w-12 h-6 rounded-full transition-colors ${notifications.critical ? 'bg-purple-500' : 'bg-gray-600'}`}
            >
              <span className={`block w-5 h-5 bg-white rounded-full transition-transform ${notifications.critical ? 'translate-x-6' : 'translate-x-0.5'}`} />
            </button>
          </div>
          
          <div className="flex items-center justify-between py-2 border-t border-[#374151]">
            <div>
              <p className="font-medium">High Severity</p>
              <p className="text-sm text-gray-400">Alert for high severity incidents</p>
            </div>
            <button 
              onClick={() => setNotifications({...notifications, high: !notifications.high})}
              className={`w-12 h-6 rounded-full transition-colors ${notifications.high ? 'bg-purple-500' : 'bg-gray-600'}`}
            >
              <span className={`block w-5 h-5 bg-white rounded-full transition-transform ${notifications.high ? 'translate-x-6' : 'translate-x-0.5'}`} />
            </button>
          </div>
          
          <div className="flex items-center justify-between py-2 border-t border-[#374151]">
            <div>
              <p className="font-medium">Email Notifications</p>
              <p className="text-sm text-gray-400">Send alerts to your email</p>
            </div>
            <button 
              onClick={() => setNotifications({...notifications, email: !notifications.email})}
              className={`w-12 h-6 rounded-full transition-colors ${notifications.email ? 'bg-purple-500' : 'bg-gray-600'}`}
            >
              <span className={`block w-5 h-5 bg-white rounded-full transition-transform ${notifications.email ? 'translate-x-6' : 'translate-x-0.5'}`} />
            </button>
          </div>
        </div>
      </div>

      {/* Appearance */}
      <div className="bg-[#1a1f2e] rounded-xl border border-[#374151] p-6">
        <h2 className="text-lg font-semibold flex items-center gap-2 mb-4">
          <Moon className="w-5 h-5 text-yellow-400" />
          Appearance
        </h2>
        
        <div className="flex gap-4">
          <button 
            onClick={() => setTheme('dark')}
            className={`flex-1 p-4 rounded-lg border transition-all ${
              theme === 'dark' 
                ? 'border-purple-500 bg-purple-500/10' 
                : 'border-[#374151] hover:border-purple-500/50'
            }`}
          >
            <Moon className="w-6 h-6 mx-auto mb-2" />
            <p className="font-medium">Dark</p>
          </button>
          <button 
            onClick={() => setTheme('light')}
            className={`flex-1 p-4 rounded-lg border transition-all ${
              theme === 'light' 
                ? 'border-purple-500 bg-purple-500/10' 
                : 'border-[#374151] hover:border-purple-500/50'
            }`}
          >
            <Sun className="w-6 h-6 mx-auto mb-2" />
            <p className="font-medium">Light</p>
          </button>
        </div>
      </div>

      {/* BRAIN Connection */}
      <div className="bg-[#1a1f2e] rounded-xl border border-[#374151] p-6">
        <h2 className="text-lg font-semibold flex items-center gap-2 mb-4">
          <Database className="w-5 h-5 text-green-400" />
          BRAIN Connection
        </h2>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm text-gray-400 mb-2">API Endpoint</label>
            <input 
              type="text"
              defaultValue="http://localhost:8000"
              className="w-full px-4 py-2 bg-[#111827] rounded-lg border border-[#374151] focus:border-purple-500 focus:outline-none"
            />
          </div>
          
          <div className="flex items-center gap-2 text-sm">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
            <span className="text-green-400">Connected</span>
            <span className="text-gray-400">• Version 1.7.0</span>
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex justify-end">
        <button className="flex items-center gap-2 px-6 py-2 bg-purple-500 hover:bg-purple-600 rounded-lg transition-colors">
          <Save className="w-4 h-4" />
          Save Changes
        </button>
      </div>
    </div>
  )
}
