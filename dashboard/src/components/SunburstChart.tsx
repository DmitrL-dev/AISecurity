'use client'

import { useState } from 'react'

interface ThreatCategory {
  name: string
  value: number
  color: string
  percentage: number
}

const threatData: ThreatCategory[] = [
  { name: 'Prompt Injection', value: 181, color: '#8b5cf6', percentage: 48.3 },
  { name: 'Jailbreaks', value: 55, color: '#06b6d4', percentage: 14.7 },
  { name: 'Data Exfiltration', value: 46, color: '#f59e0b', percentage: 12.2 },
  { name: 'MCP Attacks', value: 41, color: '#10b981', percentage: 10.9 },
  { name: 'Other', value: 52, color: '#6b7280', percentage: 13.9 },
]

const totalThreats = threatData.reduce((sum, t) => sum + t.value, 0)

export function SunburstChart() {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)
  
  // Calculate arc angles
  let currentAngle = 0
  const arcs = threatData.map((threat, idx) => {
    const angle = (threat.value / totalThreats) * 360
    const startAngle = currentAngle
    currentAngle += angle
    return { ...threat, startAngle, endAngle: currentAngle, idx }
  })

  const createArcPath = (startAngle: number, endAngle: number, innerRadius: number, outerRadius: number) => {
    const startRad = (startAngle - 90) * Math.PI / 180
    const endRad = (endAngle - 90) * Math.PI / 180
    
    const x1 = 50 + innerRadius * Math.cos(startRad)
    const y1 = 50 + innerRadius * Math.sin(startRad)
    const x2 = 50 + outerRadius * Math.cos(startRad)
    const y2 = 50 + outerRadius * Math.sin(startRad)
    const x3 = 50 + outerRadius * Math.cos(endRad)
    const y3 = 50 + outerRadius * Math.sin(endRad)
    const x4 = 50 + innerRadius * Math.cos(endRad)
    const y4 = 50 + innerRadius * Math.sin(endRad)
    
    const largeArc = endAngle - startAngle > 180 ? 1 : 0
    
    return `M ${x1} ${y1} L ${x2} ${y2} A ${outerRadius} ${outerRadius} 0 ${largeArc} 1 ${x3} ${y3} L ${x4} ${y4} A ${innerRadius} ${innerRadius} 0 ${largeArc} 0 ${x1} ${y1}`
  }

  return (
    <div className="bg-gradient-to-br from-[#1a1f2e] to-[#151922] rounded-xl border border-[#374151] p-6">
      <h3 className="text-lg font-semibold mb-4">Threat Breakdown</h3>
      
      <div className="flex items-center gap-8">
        {/* Sunburst Chart */}
        <div className="relative w-56 h-56 flex-shrink-0">
          <svg viewBox="0 0 100 100" className="w-full h-full">
            <defs>
              {threatData.map((t, i) => (
                <filter key={i} id={`glow-${i}`} x="-50%" y="-50%" width="200%" height="200%">
                  <feGaussianBlur stdDeviation="2" result="blur" />
                  <feMerge>
                    <feMergeNode in="blur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              ))}
            </defs>
            
            {/* Outer ring */}
            {arcs.map((arc, i) => (
              <path
                key={`outer-${i}`}
                d={createArcPath(arc.startAngle, arc.endAngle, 28, 44)}
                fill={arc.color}
                className="transition-all duration-300 cursor-pointer"
                style={{ 
                  filter: hoveredIndex === i ? `drop-shadow(0 0 8px ${arc.color})` : 'none',
                  transform: hoveredIndex === i ? 'scale(1.02)' : 'scale(1)',
                  transformOrigin: '50% 50%',
                  opacity: hoveredIndex !== null && hoveredIndex !== i ? 0.5 : 1
                }}
                onMouseEnter={() => setHoveredIndex(i)}
                onMouseLeave={() => setHoveredIndex(null)}
              />
            ))}
            
            {/* Inner ring */}
            {arcs.map((arc, i) => (
              <path
                key={`inner-${i}`}
                d={createArcPath(arc.startAngle, arc.endAngle, 16, 26)}
                fill={arc.color}
                opacity={hoveredIndex !== null && hoveredIndex !== i ? 0.4 : 0.6}
                className="transition-all duration-300 cursor-pointer"
                onMouseEnter={() => setHoveredIndex(i)}
                onMouseLeave={() => setHoveredIndex(null)}
              />
            ))}
            
            {/* Center circle */}
            <circle cx="50" cy="50" r="14" fill="#1a1f2e" />
          </svg>
          
          {/* Center text */}
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
            <span className="text-3xl font-bold">
              {hoveredIndex !== null ? threatData[hoveredIndex].value : totalThreats}
            </span>
            <span className="text-[10px] text-gray-400 text-center leading-tight">
              {hoveredIndex !== null ? threatData[hoveredIndex].name : 'Total Threats'}
            </span>
          </div>
        </div>
        
        {/* Legend */}
        <div className="flex-1 space-y-2">
          {threatData.map((threat, i) => (
            <div 
              key={i} 
              className={`
                flex items-center gap-3 p-2 rounded-lg transition-all duration-200 cursor-pointer
                ${hoveredIndex === i ? 'bg-white/5' : 'hover:bg-white/5'}
              `}
              onMouseEnter={() => setHoveredIndex(i)}
              onMouseLeave={() => setHoveredIndex(null)}
            >
              <span 
                className="w-3 h-3 rounded flex-shrink-0 transition-transform duration-200"
                style={{ 
                  backgroundColor: threat.color,
                  transform: hoveredIndex === i ? 'scale(1.3)' : 'scale(1)'
                }}
              />
              <span className="flex-1 text-sm">{threat.name}</span>
              <span className="text-sm font-semibold tabular-nums">{threat.percentage}%</span>
              <span className="text-xs text-gray-500 w-8 text-right tabular-nums">{threat.value}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
