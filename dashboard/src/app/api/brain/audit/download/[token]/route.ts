import { NextRequest, NextResponse } from 'next/server'

const BRAIN_API_URL = process.env.BRAIN_API_URL || 'http://localhost:8000'

interface RouteParams {
  params: Promise<{ token: string }>
}

export async function GET(request: NextRequest, { params }: RouteParams) {
  const { token } = await params

  try {
    const res = await fetch(`${BRAIN_API_URL}/v1/audit/download/${token}`, {
      cache: 'no-store',
    })

    if (!res.ok) {
      const error = await res.json()
      return NextResponse.json(error, { status: res.status })
    }

    // Get content disposition header for filename
    const contentDisposition = res.headers.get('content-disposition')
    const contentType = res.headers.get('content-type') || 'application/octet-stream'

    // Stream the response
    const blob = await res.blob()

    return new NextResponse(blob, {
      headers: {
        'Content-Type': contentType,
        'Content-Disposition': contentDisposition || 'attachment; filename=audit_export.json',
      },
    })
  } catch (_error) {
    return NextResponse.json(
      { error: 'Failed to download export' },
      { status: 500 }
    )
  }
}
