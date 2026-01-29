import { NextRequest, NextResponse } from 'next/server';
import { BRAIN_API_URL } from '@/lib/brain-api';

// Mock response when BRAIN is unavailable
function generateMockResponse(text: string) {
  const lowerText = text.toLowerCase();
  
  // Check for common attack patterns
  const injectionPatterns = ['ignore', 'forget', 'previous instructions', 'system prompt', 'dan', 'jailbreak'];
  const piiPatterns = ['ssn', 'social security', 'credit card', 'password', 'api key'];
  
  const hasInjection = injectionPatterns.some(p => lowerText.includes(p));
  const hasPII = piiPatterns.some(p => lowerText.includes(p));
  
  if (hasInjection || hasPII) {
    return {
      is_safe: false,
      risk_score: hasInjection ? 0.85 : 0.65,
      processing_time_ms: Math.floor(50 + Math.random() * 100),
      detections: [
        ...(hasInjection ? [{ engine: 'injection', threat_type: 'Prompt Injection', confidence: 0.9, details: 'Detected instruction override attempt' }] : []),
        ...(hasPII ? [{ engine: 'pii', threat_type: 'PII Request', confidence: 0.8, details: 'Detected sensitive data request' }] : []),
      ],
    };
  }
  
  return {
    is_safe: true,
    risk_score: Math.random() * 0.2,
    processing_time_ms: Math.floor(30 + Math.random() * 50),
    detections: [],
  };
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const text = body.prompt || body.text || '';
    
    // Try BRAIN API first
    try {
      const brainPayload = {
        text,
        context: body.context || {},
        engines: body.engines || [],
      };
      
      const url = `${BRAIN_API_URL}/v1/analyze`;
      console.log(`[BRAIN] Calling: ${url}`);
      
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(brainPayload),
        signal: AbortSignal.timeout(30000), // 30s timeout for first request (model loading)
      });
      
      console.log(`[BRAIN] Response status: ${res.status}`);
      
      if (res.ok) {
        const data = await res.json();
        console.log(`[BRAIN] Success, risk_score: ${data.risk_score}`);
        return NextResponse.json({
          ...data,
          is_safe: data.verdict === 'ALLOW' || data.is_safe,
          latency_ms: data.latency_ms,
        });
      } else {
        const errorText = await res.text();
        console.error(`[BRAIN] Error response: ${errorText}`);
      }
    } catch (e) {
      console.error(`[BRAIN] Connection error:`, e);
    }
    
    // Fallback to mock response
    console.log('[BRAIN] Using mock fallback');
    const mockData = generateMockResponse(text);
    return NextResponse.json({
      ...mockData,
      _mock: true,
    });
  } catch (error) {
    console.error('[BRAIN] Fatal error:', error);
    return NextResponse.json(
      { error: 'Failed to analyze' },
      { status: 500 }
    );
  }
}
