import { NextRequest, NextResponse } from 'next/server';
import { BRAIN_API_URL } from '@/lib/brain-api';

// API key for BRAIN - from environment
const API_KEY = process.env.BRAIN_API_KEY || 'sentinel-dev-key-change-me';

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ name: string; action: string }> }
) {
  try {
    const { name, action } = await params;
    
    // Validate action
    if (!['enable', 'disable'].includes(action)) {
      return NextResponse.json(
        { error: 'Invalid action. Use "enable" or "disable"' },
        { status: 400 }
      );
    }

    const url = `${BRAIN_API_URL}/v1/engines/${name}/${action}`;
    
    const res = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-SENTINEL-API-KEY': API_KEY,
      },
      signal: AbortSignal.timeout(5000),
    });

    const data = await res.json();

    if (!res.ok) {
      return NextResponse.json(data, { status: res.status });
    }

    return NextResponse.json(data);
    
  } catch (error) {
    console.error('[Toggle] Error:', error);
    return NextResponse.json(
      { error: 'Failed to toggle engine' },
      { status: 500 }
    );
  }
}
