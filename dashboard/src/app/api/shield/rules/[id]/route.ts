import { NextRequest, NextResponse } from 'next/server';

const SHIELD_URL = process.env.SHIELD_URL || 'http://localhost:8081';

interface RouteParams {
  params: Promise<{ id: string }>;
}

export async function POST(
  request: NextRequest,
  { params }: RouteParams
) {
  try {
    const { id } = await params;
    const body = await request.json();
    const response = await fetch(`${SHIELD_URL}/rules/${id}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!response.ok) throw new Error('Shield not responding');
    return NextResponse.json(await response.json());
  } catch {
    return NextResponse.json({ error: 'Shield connection failed' }, { status: 503 });
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: RouteParams
) {
  try {
    const { id } = await params;
    const response = await fetch(`${SHIELD_URL}/rules/${id}`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error('Shield not responding');
    return NextResponse.json(await response.json());
  } catch {
    return NextResponse.json({ error: 'Shield connection failed' }, { status: 503 });
  }
}
