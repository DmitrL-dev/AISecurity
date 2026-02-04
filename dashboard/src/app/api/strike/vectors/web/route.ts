import { NextResponse } from 'next/server'

const STRIKE_API_URL = process.env.STRIKE_API_URL || 'http://localhost:8001'

export async function GET() {
  try {
    const response = await fetch(`${STRIKE_API_URL}/vectors/web`, {
      cache: 'no-store',
    })

    if (!response.ok) {
      throw new Error(`Strike API error: ${response.status}`)
    }

    const data = await response.json()
    return NextResponse.json(data)
  } catch (_error) {
    console.error('Failed to fetch web vectors:', _error)
    return NextResponse.json(
      { error: 'Failed to fetch web vectors' },
      { status: 500 }
    )
  }
}
