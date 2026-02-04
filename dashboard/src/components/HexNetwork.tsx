'use client'

import { useEffect, useState, useRef, useCallback } from 'react'
import dynamic from 'next/dynamic'

// Dynamic import to avoid SSR issues
const ForceGraph2D = dynamic(() => import('react-force-graph-2d'), { ssr: false })

interface GraphNode {
  id: string
  label: string
  type: 'core' | 'service' | 'threat' | 'client'
  status: 'online' | 'offline' | 'warning' | 'critical'
  details?: string
  val?: number // node size
}

interface GraphLink {
  source: string
  target: string
  type: 'api' | 'data' | 'threat'
}

interface GraphData {
  nodes: GraphNode[]
  links: GraphLink[]
}

const nodeColors: Record<string, string> = {
  core: '#8b5cf6',
  service: '#06b6d4',
  client: '#22c55e',
  threat: '#ef4444',
}

export function HexNetwork() {
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] })
  const [threatCount, setThreatCount] = useState(0)
  const [dimensions, setDimensions] = useState({ width: 800, height: 280 })
  const containerRef = useRef<HTMLDivElement>(null)
  const graphRef = useRef<any>(null)

  // Responsive sizing
  useEffect(() => {
    function updateSize() {
      if (containerRef.current) {
        setDimensions({
          width: containerRef.current.offsetWidth,
          height: 280
        })
      }
    }
    updateSize()
    window.addEventListener('resize', updateSize)
    return () => window.removeEventListener('resize', updateSize)
  }, [])

  // Fetch topology
  useEffect(() => {
    fetchTopology()
    const interval = setInterval(fetchTopology, 15000)
    return () => clearInterval(interval)
  }, [])

  async function fetchTopology() {
    const nodes: GraphNode[] = []
    const links: GraphLink[] = []
    
    // FIXED positions for stable layout (no jumping!)
    // Layout: THREATS attacks from outside, CLIENTS above
    const positions: Record<string, {x: number, y: number}> = {
      threats:   { x: -160, y: 40 },   // Bottom left - attacking perimeter
      clients:   { x: -100, y: -40 },  // Top left - legitimate users
      shield:    { x: 0, y: 0 },       // Center - perimeter gateway
      brain:     { x: 80, y: 40 },     // ML detection
      dashboard: { x: 80, y: -40 },    // Monitoring hub  
      strike:    { x: 160, y: 0 },     // Red team testing
    }
    
    // Core - Dashboard (monitoring hub)
    nodes.push({
      id: 'dashboard', label: 'DASHBOARD', type: 'core',
      status: 'online', val: 18,
      fx: positions.dashboard.x, fy: positions.dashboard.y // FIXED position
    } as any)
    
    // Clients (external)
    nodes.push({
      id: 'clients', label: 'CLIENTS', type: 'client',
      status: 'online', val: 14,
      fx: positions.clients.x, fy: positions.clients.y
    } as any)
    
    // Check Shield (perimeter gateway)
    let shieldOnline = false
    try {
      const res = await fetch('/api/shield/health')
      shieldOnline = res.ok
      nodes.push({
        id: 'shield', label: 'SHIELD', type: 'service',
        status: shieldOnline ? 'online' : 'offline',
        details: 'Perimeter Gateway', val: 16,
        fx: positions.shield.x, fy: positions.shield.y
      } as any)
    } catch {
      nodes.push({ id: 'shield', label: 'SHIELD', type: 'service', status: 'offline', val: 16,
        fx: positions.shield.x, fy: positions.shield.y } as any)
    }
    
    // Check Brain (ML detection)
    let brainOnline = false
    try {
      const res = await fetch('/api/brain/health')
      brainOnline = res.ok
      nodes.push({
        id: 'brain', label: 'BRAIN', type: 'service',
        status: brainOnline ? 'online' : 'offline',
        details: 'ML Detection', val: 16,
        fx: positions.brain.x, fy: positions.brain.y
      } as any)
    } catch {
      nodes.push({ id: 'brain', label: 'BRAIN', type: 'service', status: 'offline', val: 16,
        fx: positions.brain.x, fy: positions.brain.y } as any)
    }
    
    // Check Strike (offensive testing)
    let strikeOnline = false
    try {
      const res = await fetch('/api/strike/status')
      strikeOnline = res.ok
      nodes.push({
        id: 'strike', label: 'STRIKE', type: 'service',
        status: strikeOnline ? 'online' : 'offline',
        details: 'Red Team', val: 14,
        fx: positions.strike.x, fy: positions.strike.y
      } as any)
    } catch {
      nodes.push({ id: 'strike', label: 'STRIKE', type: 'service', status: 'offline', val: 14,
        fx: positions.strike.x, fy: positions.strike.y } as any)
    }
    
    // REAL ARCHITECTURE LINKS:
    // Clients → Shield (all traffic goes through)
    links.push({ source: 'clients', target: 'shield', type: 'data' })
    // Shield → Brain (ML analysis)
    links.push({ source: 'shield', target: 'brain', type: 'api' })
    // Dashboard monitors all
    links.push({ source: 'dashboard', target: 'shield', type: 'api' })
    links.push({ source: 'dashboard', target: 'brain', type: 'api' })
    links.push({ source: 'dashboard', target: 'strike', type: 'api' })
    // Strike → Brain (attack testing)
    links.push({ source: 'strike', target: 'brain', type: 'api' })
    
    // Fetch threats and aggregate (show as ONE node, not many)
    let shieldBlocked = 0
    let brainBlocked = 0
    
    try {
      const historyRes = await fetch('/api/shield/history')
      if (historyRes.ok) {
        const history = await historyRes.json()
        shieldBlocked = (history || []).filter((h: any) => h.verdict === 'block').length
      }
    } catch { /* no shield */ }
    
    try {
      const strikeRes = await fetch('/api/strike/attacks')
      if (strikeRes.ok) {
        const attacks = await strikeRes.json()
        brainBlocked = (attacks || []).reduce((sum: number, a: any) => 
          sum + (a.findings?.length || 0), 0)
      }
    } catch { /* no strike */ }
    
    const totalBlocked = shieldBlocked + brainBlocked
    setThreatCount(totalBlocked)
    
    // Add SINGLE aggregated threat node if there are threats
    if (totalBlocked > 0) {
      nodes.push({
        id: 'threats',
        label: `🛡️ ${totalBlocked}`,
        type: 'threat',
        status: 'critical',
        val: Math.min(12 + totalBlocked, 20),
        fx: positions.threats.x, fy: positions.threats.y // FIXED outside
      } as any)
      // Threats attack Shield (perimeter)
      links.push({ source: 'threats', target: 'shield', type: 'threat' })
    }
    
    setGraphData({ nodes, links })
  }
  
  function _formatThreatLabel(type: string): string {
    const t = type.toLowerCase()
    if (t.includes('injection')) return 'Injection'
    if (t.includes('jailbreak')) return 'Jailbreak'
    if (t.includes('exfil')) return 'Data Exfil'
    if (t.includes('pii')) return 'PII Leak'
    if (t.includes('manipulation')) return 'Manipulation'
    return type.slice(0, 12)
  }

  const nodeCanvasObject = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const label = node.label
    const fontSize = Math.max(10 / globalScale, 3)
    ctx.font = `bold ${fontSize}px Inter, sans-serif`
    
    const size = node.val || 10
    const color = nodeColors[node.type] || '#6b7280'
    const isOffline = node.status === 'offline'
    
    // Draw hexagon
    ctx.beginPath()
    for (let i = 0; i < 6; i++) {
      const angle = (Math.PI / 3) * i - Math.PI / 2
      const x = node.x + size * Math.cos(angle)
      const y = node.y + size * Math.sin(angle)
      if (i === 0) ctx.moveTo(x, y)
      else ctx.lineTo(x, y)
    }
    ctx.closePath()
    
    // Fill
    ctx.globalAlpha = isOffline ? 0.4 : 1
    ctx.fillStyle = color
    ctx.fill()
    
    // Glow for threats
    if (node.type === 'threat') {
      ctx.shadowColor = color
      ctx.shadowBlur = 10
      ctx.stroke()
      ctx.shadowBlur = 0
    }
    
    // Border
    ctx.strokeStyle = isOffline ? '#6b7280' : color
    ctx.lineWidth = 2 / globalScale
    ctx.stroke()
    ctx.globalAlpha = 1
    
    // Label
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillStyle = 'white'
    ctx.fillText(label, node.x, node.y)
    
    // Status indicator for offline
    if (isOffline) {
      ctx.beginPath()
      ctx.arc(node.x + size * 0.7, node.y - size * 0.7, 4 / globalScale, 0, 2 * Math.PI)
      ctx.fillStyle = '#6b7280'
      ctx.fill()
    }
  }, [])

  const linkColor = useCallback((link: any) => {
    if (link.type === 'threat') return 'rgba(239, 68, 68, 0.6)'
    if (link.type === 'api') return 'rgba(139, 92, 246, 0.5)'
    return 'rgba(6, 182, 212, 0.5)'
  }, [])

  const linkWidth = useCallback((link: any) => {
    return link.type === 'threat' ? 1 : 2
  }, [])

  const onlineServices = graphData.nodes.filter(n => n.type === 'service' && n.status === 'online').length
  const totalServices = graphData.nodes.filter(n => n.type === 'service').length

  return (
    <div className="bg-[#1a1f2e] rounded-xl border border-[#374151] p-4 overflow-hidden">
      <div className="flex justify-between items-start mb-2">
        <div>
          <h3 className="text-lg font-semibold">System Topology & Active Threats</h3>
          <p className="text-sm text-gray-400">
            Services: {onlineServices}/{totalServices} online | Threats blocked: {threatCount}
            <span className="ml-2 text-gray-500 text-xs">(drag to move, scroll to zoom)</span>
          </p>
        </div>
      </div>
      
      <div ref={containerRef} className="w-full" style={{ height: 280 }}>
        {typeof window !== 'undefined' && graphData.nodes.length > 0 && (
          <ForceGraph2D
            ref={graphRef}
            graphData={graphData}
            width={dimensions.width}
            height={dimensions.height}
            backgroundColor="transparent"
            nodeCanvasObject={nodeCanvasObject}
            nodePointerAreaPaint={(node: any, color, ctx) => {
              const size = node.val || 10
              ctx.beginPath()
              ctx.arc(node.x, node.y, size, 0, 2 * Math.PI)
              ctx.fillStyle = color
              ctx.fill()
            }}
            linkColor={linkColor}
            linkWidth={linkWidth}
            linkDirectionalParticles={2}
            linkDirectionalParticleWidth={2}
            linkDirectionalParticleSpeed={0.005}
            enablePanInteraction={true}
            enableZoomInteraction={true}
            enableNodeDrag={false}
            cooldownTicks={0}
            onEngineStop={() => graphRef.current?.zoomToFit(400, 50)}
          />
        )}
      </div>
      
      {/* Legend */}
      <div className="flex gap-6 mt-2 text-xs">
        <span className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-purple-500" /> Core
        </span>
        <span className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-cyan-500" /> Service
        </span>
        <span className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-green-500" /> Client
        </span>
        <span className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-red-500" /> Threat
        </span>
      </div>
    </div>
  )
}
