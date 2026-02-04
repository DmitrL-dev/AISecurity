import { NextResponse } from 'next/server';

// Strike API URL
const STRIKE_API_URL = process.env.STRIKE_API_URL || 'http://localhost:8001';

/**
 * GET /api/strike/vectors - List available attack vectors
 */
export async function GET() {
  try {
    const res = await fetch(`${STRIKE_API_URL}/vectors`, {
      signal: AbortSignal.timeout(5000),
    });
    
    if (!res.ok) {
      // Return mock data if Strike API not available
      return NextResponse.json({
        jailbreaks: 25,
        prompt_injection: 18,
        data_poisoning: 12,
        protocol_attacks: 8,
        data_exfil: 6,
      });
    }
    
    const data = await res.json();
    return NextResponse.json(data);
  } catch (_error) {
    console.error('[Strike] Vectors fetch failed:', _error);
    // Return mock data as fallback
    return NextResponse.json({
      jailbreaks: 25,
      prompt_injection: 18,
      data_poisoning: 12,
      protocol_attacks: 8,
      data_exfil: 6,
    });
  }
}
