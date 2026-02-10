import { NextResponse } from 'next/server';
import { BRAIN_API_URL } from '@/lib/brain-api';

export async function GET() {
  try {
    const res = await fetch(`${BRAIN_API_URL}/v1/engines`, {
      cache: 'no-store',
    });
    
    if (!res.ok) {
      return NextResponse.json(
        { error: 'Failed to fetch engines' },
        { status: res.status }
      );
    }
    
    const data = await res.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to connect to BRAIN API' },
      { status: 503 }
    );
  }
}
