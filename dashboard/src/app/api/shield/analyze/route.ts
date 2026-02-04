import { NextRequest, NextResponse } from 'next/server';

const SHIELD_URL = process.env.SHIELD_URL || 'http://localhost:8081';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    
    const response = await fetch(`${SHIELD_URL}/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    
    if (!response.ok) {
      return NextResponse.json({ error: 'Shield analysis failed' }, { status: 502 });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (_error) {
    return NextResponse.json({ error: 'Shield connection failed' }, { status: 503 });
  }
}
