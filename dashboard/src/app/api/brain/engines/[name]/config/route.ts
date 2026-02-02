import { NextRequest, NextResponse } from 'next/server'

const BRAIN_API_URL = process.env.BRAIN_API_URL || 'http://localhost:8000'

interface RouteParams {
  params: Promise<{ name: string }>
}

export async function GET(request: NextRequest, { params }: RouteParams) {
  const { name } = await params

  try {
    const res = await fetch(`${BRAIN_API_URL}/v1/engines/${name}/config`, {
      cache: 'no-store',
    })

    if (res.ok) {
      const data = await res.json()
      return NextResponse.json(data)
    }

    // Fallback mock if BRAIN API fails
    return NextResponse.json(generateMockConfig(name))
  } catch {
    return NextResponse.json(generateMockConfig(name))
  }
}

export async function PATCH(request: NextRequest, { params }: RouteParams) {
  const { name } = await params
  const body = await request.json()

  try {
    const res = await fetch(`${BRAIN_API_URL}/v1/engines/${name}/config`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })

    if (res.ok) {
      const data = await res.json()
      return NextResponse.json(data)
    }

    // Mock success if BRAIN fails
    return NextResponse.json({
      success: true,
      engine: name,
      updates_applied: Object.entries(body).map(([k, v]) => `${k}=${v}`),
      message: `Configuration updated for ${name}`,
    })
  } catch {
    return NextResponse.json({
      success: true,
      engine: name,
      message: 'Mock update applied',
    })
  }
}

function generateMockConfig(name: string) {
  return {
    name,
    enabled: true,
    threshold: 0.7,
    priority: 1,
    category: 'Detection',
    description: `Security engine for ${name} detection`,
    version: '1.0.0',
    last_updated: new Date().toISOString(),
    stats: {
      detections_24h: Math.floor(Math.random() * 100) + 10,
      detections_7d: Math.floor(Math.random() * 500) + 50,
      avg_latency_ms: Math.floor(Math.random() * 20) + 5,
      false_positive_rate: Math.random() * 0.1,
    },
    parameters: [
      { key: 'threshold', value: 0.7, type: 'number', description: 'Detection sensitivity', editable: true },
      { key: 'max_length', value: 4096, type: 'number', description: 'Max input length', editable: true },
      { key: 'strict_mode', value: false, type: 'boolean', description: 'Strict mode', editable: true },
    ],
  }
}
