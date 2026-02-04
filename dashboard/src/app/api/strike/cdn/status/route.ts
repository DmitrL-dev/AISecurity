import { NextResponse } from 'next/server';

const STRIKE_API_URL = process.env.STRIKE_API_URL || 'http://localhost:8001';

export async function GET() {
  try {
    const response = await fetch(`${STRIKE_API_URL}/cdn/status`, {
      cache: 'no-store',
    });

    if (!response.ok) {
      return NextResponse.json(
        { state: 'failed', error: `Strike API returned ${response.status}` },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (_error) {
    console.error('CDN status fetch failed:', _error);
    return NextResponse.json(
      { state: 'failed', error: 'Failed to connect to Strike API' },
      { status: 503 }
    );
  }
}
