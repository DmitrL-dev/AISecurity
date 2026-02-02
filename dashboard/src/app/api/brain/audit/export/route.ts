import { NextRequest, NextResponse } from 'next/server'

const BRAIN_API_URL = process.env.BRAIN_API_URL || 'http://localhost:8000'
const API_KEY = process.env.SENTINEL_API_KEY || 'sentinel-dev-key-change-me'

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()

    const res = await fetch(`${BRAIN_API_URL}/v1/audit/export`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-SENTINEL-API-KEY': API_KEY,
      },
      body: JSON.stringify(body),
    })

    if (res.ok) {
      const data = await res.json()
      return NextResponse.json(data)
    }

    const error = await res.json()
    return NextResponse.json(error, { status: res.status })
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to create export' },
      { status: 500 }
    )
  }
}
