import { NextResponse } from 'next/server'

const STRIKE_API_URL = process.env.STRIKE_API_URL || 'http://strike:8001'

export async function GET() {
  try {
    const res = await fetch(`${STRIKE_API_URL}/`, {
      cache: 'no-store',
      headers: { 'Accept': 'application/json' }
    })

    if (!res.ok) {
      return NextResponse.json(
        { error: 'Strike API error', status: res.status },
        { status: res.status }
      )
    }

    const data = await res.json()
    return NextResponse.json(data)
  } catch (_error) {
    console.error('Strike API fetch failed:', _error)
    return NextResponse.json(
      { error: 'Failed to connect to Strike API' },
      { status: 503 }
    )
  }
}
