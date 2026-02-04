import { NextResponse } from 'next/server'

// Strike API URL
const STRIKE_API_URL = process.env.STRIKE_API_URL || 'http://localhost:8001'

/**
 * POST /api/strike/attacks/[id]/pause - Pause attack
 */
export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params
    
    const res = await fetch(`${STRIKE_API_URL}/attack/${id}/pause`, {
      method: 'POST',
      signal: AbortSignal.timeout(10000),
    })
    
    if (!res.ok) {
      const error = await res.text()
      return NextResponse.json(
        { error: `Failed to pause attack: ${error}` },
        { status: res.status }
      )
    }
    
    const data = await res.json()
    return NextResponse.json(data)
  } catch (_error) {
    console.error('[Strike] Pause attack failed:', _error)
    return NextResponse.json(
      { error: 'Failed to pause attack' },
      { status: 500 }
    )
  }
}
