import { NextResponse } from 'next/server';
import { BRAIN_API_URL } from '@/lib/brain-api';

export async function GET() {
  try {
    const res = await fetch(`${BRAIN_API_URL}/v1/engines/status`, {
      signal: AbortSignal.timeout(5000),
    });
    
    if (res.ok) {
      const data = await res.json();
      return NextResponse.json(data);
    }
    
    // Fallback if BRAIN unavailable
    return NextResponse.json({
      profile: 'unknown',
      total_registered: 0,
      active_engines: 0,
      by_tier: {},
      _mock: true,
    });
    
  } catch (error) {
    console.error('[BRAIN] Engine status error:', error);
    return NextResponse.json({
      profile: 'unknown',
      total_registered: 0,
      active_engines: 0,
      by_tier: {},
      _mock: true,
    });
  }
}
