import { NextResponse } from 'next/server';
import { BRAIN_API_URL } from '@/lib/brain-api';

export async function GET() {
  try {
    const res = await fetch(`${BRAIN_API_URL}/health`, {
      cache: 'no-store',
    });
    
    if (!res.ok) {
      return NextResponse.json(
        { error: 'BRAIN API unavailable', status: 'unhealthy' },
        { status: 503 }
      );
    }
    
    const data = await res.json();
    return NextResponse.json(data);
  } catch (_error) {
    return NextResponse.json(
      { error: 'Failed to connect to BRAIN API', status: 'unhealthy' },
      { status: 503 }
    );
  }
}
