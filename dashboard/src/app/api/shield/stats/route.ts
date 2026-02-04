import { NextResponse } from 'next/server';

const SHIELD_URL = process.env.SHIELD_URL || 'http://localhost:8081';

export async function GET() {
  try {
    const response = await fetch(`${SHIELD_URL}/stats`, { cache: 'no-store' });
    if (!response.ok) throw new Error('Shield not responding');
    return NextResponse.json(await response.json());
  } catch {
    return NextResponse.json({ error: 'Shield connection failed' }, { status: 503 });
  }
}
