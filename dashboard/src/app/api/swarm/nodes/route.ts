/**
 * Swarm API Routes
 * 
 * GET /api/swarm/nodes - List all nodes in the swarm
 * GET /api/swarm/stats - Get aggregated swarm statistics
 */

import { NextResponse } from 'next/server'

// Mock data for development - will connect to BRAIN API in production
const BRAIN_API_URL = process.env.BRAIN_API_URL || 'http://localhost:8000'

interface SwarmNode {
  node_id: string
  hostname: string
  port: number
  version: string
  status: 'online' | 'degraded' | 'offline'
  capabilities: string[]
  last_heartbeat: string
  registered_at: string
}

export async function GET() {
  try {
    // Try to fetch from BRAIN API
    const response = await fetch(`${BRAIN_API_URL}/api/v1/swarm/nodes`, {
      cache: 'no-store',
      headers: {
        'Accept': 'application/json',
      },
    })

    if (response.ok) {
      const data = await response.json()
      return NextResponse.json(data)
    }
    
    // Fallback to mock data for development
    const mockNodes: SwarmNode[] = [
      {
        node_id: 'brain-local-1',
        hostname: 'localhost',
        port: 8000,
        version: '1.0.0',
        status: 'online',
        capabilities: ['analyze', 'qwen_guard', 'collective_immunity'],
        last_heartbeat: new Date().toISOString(),
        registered_at: new Date().toISOString(),
      }
    ]

    return NextResponse.json({
      nodes: mockNodes,
      total: mockNodes.length,
      online: mockNodes.filter(n => n.status === 'online').length,
      offline: mockNodes.filter(n => n.status === 'offline').length,
    })
  } catch (_error) {
    // Return mock data on error
    return NextResponse.json({
      nodes: [{
        node_id: 'brain-local-1',
        hostname: 'localhost',
        port: 8000,
        version: '1.0.0',
        status: 'online',
        capabilities: ['analyze'],
        last_heartbeat: new Date().toISOString(),
        registered_at: new Date().toISOString(),
      }],
      total: 1,
      online: 1,
      offline: 0,
    })
  }
}
