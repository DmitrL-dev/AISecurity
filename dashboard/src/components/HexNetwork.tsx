'use client'

import { useEffect, useState } from 'react'

interface HexNode {
  id: string
  label: string
  type: 'engine' | 'threat'
  status?: 'active' | 'warning' | 'critical'
  size: number
  x: number
  y: number
}

interface Connection {
  from: string
  to: string
  type: 'data' | 'threat'
}

const nodes: HexNode[] = [
  { id: 'brain', label: 'BRAIN', type: 'engine', status: 'active', size: 50, x: 400, y: 150 },
  { id: 'guard', label: 'GUARD', type: 'engine', status: 'active', size: 40, x: 200, y: 130 },
  { id: 'strike', label: 'STRIKE', type: 'engine', status: 'active', size: 40, x: 600, y: 170 },
  
  { id: 't1', label: 'Prompt Injection', type: 'threat', status: 'critical', size: 25, x: 100, y: 60 },
  { id: 't2', label: 'Jailbreak', type: 'threat', status: 'critical', size: 25, x: 250, y: 40 },
  { id: 't3', label: 'Data Exfil', type: 'threat', status: 'warning', size: 25, x: 700, y: 80 },
  { id: 't4', label: 'MCP Attack', type: 'threat', status: 'warning', size: 25, x: 550, y: 50 },
  { id: 't5', label: 'Prompt Injection', type: 'threat', status: 'critical', size: 25, x: 450, y: 30 },
  { id: 't6', label: 'Prompt Injection', type: 'threat', status: 'warning', size: 25, x: 750, y: 160 },
]

const connections: Connection[] = [
  { from: 'brain', to: 'guard', type: 'data' },
  { from: 'brain', to: 'strike', type: 'data' },
  { from: 't1', to: 'guard', type: 'threat' },
  { from: 't2', to: 'brain', type: 'threat' },
  { from: 't3', to: 'strike', type: 'threat' },
  { from: 't4', to: 'strike', type: 'threat' },
  { from: 't5', to: 'brain', type: 'threat' },
  { from: 't6', to: 'strike', type: 'threat' },
]

// SVG Hexagon path generator
function hexagonPath(cx: number, cy: number, size: number): string {
  const points = []
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 3) * i - Math.PI / 2
    const x = cx + size * Math.cos(angle)
    const y = cy + size * Math.sin(angle)
    points.push(`${x},${y}`)
  }
  return points.join(' ')
}

function HexagonNode({ node, isAnimating }: { node: HexNode; isAnimating: boolean }) {
  const colors = {
    engine: {
      fill: 'url(#engineGradient)',
      stroke: '#06b6d4',
      glow: '#06b6d4',
    },
    threat: node.status === 'critical' ? {
      fill: 'url(#criticalGradient)',
      stroke: '#ef4444',
      glow: '#ef4444',
    } : {
      fill: 'url(#warningGradient)',
      stroke: '#f59e0b',
      glow: '#f59e0b',
    }
  }
  
  const color = colors[node.type]
  
  return (
    <g className="cursor-pointer transition-all duration-300 hover:opacity-80">
      {/* Glow effect */}
      <polygon
        points={hexagonPath(node.x, node.y, node.size + 8)}
        fill="none"
        stroke={color.glow}
        strokeWidth="2"
        opacity={isAnimating && node.type === 'threat' ? 0.6 : 0.3}
        className={isAnimating && node.type === 'threat' ? 'animate-pulse' : ''}
        style={{ filter: `drop-shadow(0 0 10px ${color.glow})` }}
      />
      
      {/* Main hexagon */}
      <polygon
        points={hexagonPath(node.x, node.y, node.size)}
        fill={color.fill}
        stroke={color.stroke}
        strokeWidth="2"
        style={{ filter: `drop-shadow(0 0 5px ${color.glow})` }}
      />
      
      {/* Label */}
      <text
        x={node.x}
        y={node.y}
        textAnchor="middle"
        dominantBaseline="middle"
        fill="white"
        fontSize={node.type === 'engine' ? 12 : 8}
        fontWeight="bold"
        className="pointer-events-none"
      >
        {node.label}
      </text>
    </g>
  )
}

function ConnectionLine({ from, to, type }: { from: HexNode; to: HexNode; type: string }) {
  const isThreat = type === 'threat'
  const color = isThreat ? '#ef4444' : '#06b6d4'
  
  return (
    <g>
      <line
        x1={from.x}
        y1={from.y}
        x2={to.x}
        y2={to.y}
        stroke={color}
        strokeWidth={isThreat ? 1.5 : 2}
        strokeDasharray={isThreat ? '5,5' : 'none'}
        opacity={0.6}
        markerEnd={isThreat ? 'url(#arrowRed)' : 'url(#arrowCyan)'}
      />
      {/* Animated particles for data flow */}
      {!isThreat && (
        <circle r="3" fill="#06b6d4">
          <animateMotion
            dur="2s"
            repeatCount="indefinite"
            path={`M${from.x},${from.y} L${to.x},${to.y}`}
          />
        </circle>
      )}
    </g>
  )
}

export function HexNetwork() {
  const [isAnimating, setIsAnimating] = useState(true)
  const nodeMap = Object.fromEntries(nodes.map(n => [n.id, n]))

  useEffect(() => {
    const interval = setInterval(() => {
      setIsAnimating(prev => !prev)
    }, 2000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="bg-[#1a1f2e] rounded-xl border border-[#374151] p-4 overflow-hidden">
      <div className="flex justify-between items-start mb-2">
        <div>
          <h3 className="text-lg font-semibold">Attack Path & Active Threats</h3>
          <p className="text-sm text-gray-400">Focus: 5 Active Kill Chains Identified</p>
        </div>
      </div>
      
      <svg viewBox="0 0 850 220" className="w-full h-auto">
        <defs>
          {/* Gradients */}
          <linearGradient id="engineGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#8b5cf6" />
            <stop offset="100%" stopColor="#06b6d4" />
          </linearGradient>
          <linearGradient id="criticalGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#ef4444" />
            <stop offset="100%" stopColor="#dc2626" />
          </linearGradient>
          <linearGradient id="warningGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#f59e0b" />
            <stop offset="100%" stopColor="#d97706" />
          </linearGradient>
          
          {/* Arrow markers */}
          <marker id="arrowRed" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
            <path d="M0,0 L0,6 L9,3 z" fill="#ef4444" />
          </marker>
          <marker id="arrowCyan" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
            <path d="M0,0 L0,6 L9,3 z" fill="#06b6d4" />
          </marker>
        </defs>
        
        {/* Connections */}
        {connections.map((conn, i) => (
          <ConnectionLine
            key={i}
            from={nodeMap[conn.from]}
            to={nodeMap[conn.to]}
            type={conn.type}
          />
        ))}
        
        {/* Nodes */}
        {nodes.map(node => (
          <HexagonNode key={node.id} node={node} isAnimating={isAnimating} />
        ))}
      </svg>
      
      {/* Legend */}
      <div className="flex gap-6 mt-2 text-xs">
        <span className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-red-500 animate-pulse" /> Critical
        </span>
        <span className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-yellow-500" /> Warning
        </span>
        <span className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-cyan-500" /> Engine
        </span>
      </div>
    </div>
  )
}
