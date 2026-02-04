import { NextRequest, NextResponse } from 'next/server'

const BRAIN_API_URL = process.env.BRAIN_API_URL || 'http://localhost:8000'
const API_KEY = process.env.SENTINEL_API_KEY || 'sentinel-dev-key-change-me'

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url)
  const period = searchParams.get('period') || '24h'

  try {
    // Try to fetch from BRAIN API
    const res = await fetch(`${BRAIN_API_URL}/v1/metrics?period=${period}`, {
      headers: {
        'X-SENTINEL-API-KEY': API_KEY,
      },
      cache: 'no-store',
    })

    if (res.ok) {
      const data = await res.json()
      return NextResponse.json(data)
    }

    // Fallback: generate mock metrics
    return NextResponse.json(generateMockMetrics(period))
  } catch (_error) {
    // API not available, return mock data
    return NextResponse.json(generateMockMetrics(period))
  }
}

function generateMockMetrics(period: string) {
  const points = period === '24h' ? 24 : period === '7d' ? 7 : 30

  const trends = Array.from({ length: points }, (_, i) => {
    const baseTime = period === '24h' 
      ? Date.now() - (points - i) * 3600000
      : Date.now() - (points - i) * 86400000

    return {
      timestamp: new Date(baseTime).toISOString(),
      total: Math.floor(Math.random() * 100) + 50,
      blocked: Math.floor(Math.random() * 80) + 30,
      allowed: Math.floor(Math.random() * 30) + 10,
    }
  })

  const engines = [
    { name: 'injection', detections: Math.floor(Math.random() * 50) + 20 },
    { name: 'jailbreak', detections: Math.floor(Math.random() * 40) + 15 },
    { name: 'pii', detections: Math.floor(Math.random() * 30) + 10 },
    { name: 'semantic', detections: Math.floor(Math.random() * 25) + 5 },
    { name: 'mcp_security', detections: Math.floor(Math.random() * 20) + 5 },
  ].sort((a, b) => b.detections - a.detections)

  return { trends, engines, period }
}
