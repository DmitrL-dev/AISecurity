import { NextResponse } from 'next/server';

// Strike API URL - runs on port 8001
const STRIKE_API_URL = process.env.STRIKE_API_URL || 'http://localhost:8001';

/**
 * GET /api/strike/health - Check Strike API health
 */
export async function GET() {
  try {
    const res = await fetch(`${STRIKE_API_URL}/health`, {
      signal: AbortSignal.timeout(5000),
    });
    
    if (!res.ok) {
      return NextResponse.json(
        { status: 'unhealthy', error: 'Strike API not responding' },
        { status: 503 }
      );
    }
    
    const data = await res.json();
    return NextResponse.json(data);
  } catch (_error) {
    console.error('[Strike] Health check failed:', _error);
    return NextResponse.json(
      { status: 'offline', error: 'Cannot connect to Strike API' },
      { status: 503 }
    );
  }
}
