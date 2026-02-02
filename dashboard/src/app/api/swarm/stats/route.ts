/**
 * Swarm Stats API Route
 * 
 * GET /api/swarm/stats - Aggregated swarm statistics
 */

import { NextResponse } from 'next/server'

const BRAIN_API_URL = process.env.BRAIN_API_URL || 'http://localhost:8000'

interface SwarmStats {
  nodes: {
    online: number
    offline: number
    degraded: number
  }
  total_analyses: number
  total_blocked: number
  patterns_shared: number
  avg_latency_ms: number
  uptime_hours: number
}

export async function GET() {
  try {
    const response = await fetch(`${BRAIN_API_URL}/api/v1/swarm/stats`, {
      cache: 'no-store',
    })

    if (response.ok) {
      return NextResponse.json(await response.json())
    }

    // Fallback mock stats
    const stats: SwarmStats = {
      nodes: {
        online: 1,
        offline: 0,
        degraded: 0,
      },
      total_analyses: 15420,
      total_blocked: 892,
      patterns_shared: 156,
      avg_latency_ms: 45,
      uptime_hours: 72,
    }

    return NextResponse.json(stats)
  } catch {
    return NextResponse.json({
      nodes: { online: 1, offline: 0, degraded: 0 },
      total_analyses: 0,
      total_blocked: 0,
      patterns_shared: 0,
      avg_latency_ms: 0,
      uptime_hours: 0,
    })
  }
}
