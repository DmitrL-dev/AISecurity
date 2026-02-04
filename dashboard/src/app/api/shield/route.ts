import { NextResponse } from 'next/server';

const SHIELD_URL = process.env.SHIELD_URL || 'http://localhost:8081';

export async function GET() {
  try {
    const response = await fetch(`${SHIELD_URL}/`, {
      cache: 'no-store',
    });
    
    if (!response.ok) {
      return NextResponse.json({ error: 'Shield not available' }, { status: 503 });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (_error) {
    return NextResponse.json({ error: 'Shield connection failed' }, { status: 503 });
  }
}
