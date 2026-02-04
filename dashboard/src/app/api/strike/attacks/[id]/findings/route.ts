import { NextResponse } from 'next/server'

// Strike API URL
const STRIKE_API_URL = process.env.STRIKE_API_URL || 'http://localhost:8001'

/**
 * GET /api/strike/attacks/[id]/findings - Get attack findings
 */
export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params
    
    const res = await fetch(`${STRIKE_API_URL}/attack/${id}/findings`, {
      signal: AbortSignal.timeout(10000),
    })
    
    if (!res.ok) {
      // Return empty findings if not found
      if (res.status === 404) {
        return NextResponse.json({ findings: [], total: 0 })
      }
      const error = await res.text()
      return NextResponse.json(
        { error: `Failed to get findings: ${error}` },
        { status: res.status }
      )
    }
    
    const data = await res.json()
    return NextResponse.json(data)
  } catch (_error) {
    console.error('[Strike] Get findings failed:', _error)
    return NextResponse.json(
      { error: 'Failed to get findings' },
      { status: 500 }
    )
  }
}
