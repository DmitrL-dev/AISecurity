import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/lib/auth';

// Strike API URL
const STRIKE_API_URL = process.env.STRIKE_API_URL || 'http://localhost:8001';

/**
 * GET /api/strike/attacks - List all attacks
 */
export async function GET() {
  try {
    const res = await fetch(`${STRIKE_API_URL}/attacks`, {
      signal: AbortSignal.timeout(5000),
    });
    
    if (!res.ok) {
      return NextResponse.json([]);
    }
    
    const data = await res.json();
    return NextResponse.json(data);
  } catch (_error) {
    console.error('[Strike] List attacks failed:', _error);
    return NextResponse.json([]);
  }
}

/**
 * POST /api/strike/attacks - Start new attack
 */
export async function POST(request: NextRequest) {
  try {
    // Get user from session for audit
    const session = await auth();
    const userEmail = session?.user?.email || 'anonymous';
    
    const body = await request.json();
    
    console.log(`[Strike] Starting attack by ${userEmail}:`, body.target);
    
    const res = await fetch(`${STRIKE_API_URL}/attack`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(10000),
    });
    
    if (!res.ok) {
      const error = await res.text();
      return NextResponse.json(
        { error: `Strike API error: ${error}` },
        { status: res.status }
      );
    }
    
    const data = await res.json();
    return NextResponse.json(data);
  } catch (_error) {
    console.error('[Strike] Start attack failed:', _error);
    return NextResponse.json(
      { error: 'Failed to start attack' },
      { status: 500 }
    );
  }
}
