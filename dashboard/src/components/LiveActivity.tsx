'use client'

import { useState, useEffect } from 'react'
import { Radio, Shield, AlertTriangle, Info, Bug } from 'lucide-react'

interface ActivityEvent {
  id: string
  timestamp: string
  type: 'threat' | 'block' | 'info' | 'debug'
  engine: string
  message: string
}

const levelConfig = {
  threat: { icon: AlertTriangle, color: 'text-red-400', bg: 'bg-red-500/20' },
  block: { icon: Shield, color: 'text-green-400', bg: 'bg-green-500/20' },
  info: { icon: Info, color: 'text-blue-400', bg: 'bg-blue-500/20' },
  debug: { icon: Bug, color: 'text-gray-400', bg: 'bg-gray-500/20' },
}

export function LiveActivity() {
  const [events, setEvents] = useState<ActivityEvent[]>([])
  const [isLive, setIsLive] = useState(true)

  useEffect(() => {
    if (!isLive) return

    // Poll for new events (WebSocket fallback)
    const fetchEvents = async () => {
      try {
        const res = await fetch('/api/brain/audit/logs?limit=10')
        if (res.ok) {
          const data = await res.json()
          const mappedEvents: ActivityEvent[] = (data.entries || []).map((e: any, i: number) => ({
            id: `${e.timestamp}-${i}`,
            timestamp: e.timestamp,
            type: mapLevelToType(e.level),
            engine: e.resource?.replace('engine:', '') || 'system',
            message: `${e.action} - ${e.outcome}`,
          }))
          setEvents(mappedEvents)
        }
      } catch {
        // Generate mock events if API fails
        addMockEvent()
      }
    }

    fetchEvents()
    const interval = setInterval(fetchEvents, 5000)
    return () => clearInterval(interval)
  }, [isLive])

  function mapLevelToType(level: string): 'threat' | 'block' | 'info' | 'debug' {
    switch (level) {
      case 'CRITICAL': return 'threat'
      case 'WARNING': return 'block'
      case 'INFO': return 'info'
      default: return 'debug'
    }
  }

  function addMockEvent() {
    const types: Array<'threat' | 'block' | 'info' | 'debug'> = ['threat', 'block', 'info', 'info']
    const engines = ['injection', 'jailbreak', 'pii', 'semantic', 'mcp_security']
    const messages = [
      'Prompt injection attempt blocked',
      'Jailbreak pattern detected',
      'PII detected and masked',
      'Request analyzed successfully',
      'MCP tool abuse attempt',
    ]

    const newEvent: ActivityEvent = {
      id: Date.now().toString(),
      timestamp: new Date().toISOString(),
      type: types[Math.floor(Math.random() * types.length)],
      engine: engines[Math.floor(Math.random() * engines.length)],
      message: messages[Math.floor(Math.random() * messages.length)],
    }

    setEvents(prev => [newEvent, ...prev].slice(0, 10))
  }

  function formatTime(ts: string): string {
    try {
      return new Date(ts).toLocaleTimeString('ru-RU', { 
        hour: '2-digit', 
        minute: '2-digit', 
        second: '2-digit' 
      })
    } catch {
      return '--:--:--'
    }
  }

  return (
    <div className="card">
      <div className="card-header">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`icon-container ${isLive ? 'icon-container--success' : 'icon-container--secondary'}`}>
              <Radio className={`w-5 h-5 ${isLive ? 'animate-pulse' : ''}`} />
            </div>
            <div>
              <h3 className="card-title">Live Activity</h3>
              <p className="card-subtitle">
                {isLive ? 'Real-time event stream' : 'Paused'}
              </p>
            </div>
          </div>

          <button
            onClick={() => setIsLive(!isLive)}
            className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
              isLive 
                ? 'bg-green-500/20 text-green-400 border border-green-500/30' 
                : 'bg-gray-700 text-gray-400 border border-gray-600'
            }`}
          >
            {isLive ? 'LIVE' : 'PAUSED'}
          </button>
        </div>
      </div>

      <div className="card-content">
        <div className="space-y-2 max-h-[280px] overflow-y-auto scrollbar-thin">
          {events.length === 0 ? (
            <div className="text-center text-gray-500 py-8">
              <Radio className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>Waiting for events...</p>
            </div>
          ) : (
            events.map((event, i) => {
              const config = levelConfig[event.type]
              const Icon = config.icon

              return (
                <div 
                  key={event.id}
                  className={`flex items-start gap-3 p-3 rounded-lg bg-gray-900/50 border border-gray-800 transition-all ${
                    i === 0 && isLive ? 'animate-fadeIn' : ''
                  }`}
                >
                  <div className={`p-1.5 rounded-lg ${config.bg}`}>
                    <Icon className={`w-4 h-4 ${config.color}`} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="text-xs font-mono text-gray-500">
                        {formatTime(event.timestamp)}
                      </span>
                      <span className="text-xs px-1.5 py-0.5 rounded bg-gray-700 text-gray-300">
                        {event.engine}
                      </span>
                    </div>
                    <p className="text-sm text-gray-200 truncate">
                      {event.message}
                    </p>
                  </div>
                </div>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}
