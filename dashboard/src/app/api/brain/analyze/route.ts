import { NextRequest, NextResponse } from 'next/server';
import { BRAIN_API_URL } from '@/lib/brain-api';

// Track if BRAIN has been successfully contacted (models loaded)
let isWarmedUp = false;

// Adaptive timeout: 60s for cold start, 5s after warmup
function getTimeout(): number {
  return isWarmedUp ? 5000 : 60000;
}

// Mock response when BRAIN is unavailable
function generateMockResponse(text: string) {
  
  // Pattern detection with scoring
  const patterns = [
    { regex: /ignore.*(?:previous|prior|above).*instructions?/i, engine: 'injection', type: 'instruction_override', score: 40 },
    { regex: /system\s*prompt/i, engine: 'prompt_leak', type: 'extraction_attempt', score: 35 },
    { regex: /(?:dan|jailbreak|bypass|pretend)/i, engine: 'jailbreak', type: 'role_manipulation', score: 45 },
    { regex: /(?:you are now|act as|roleplay)/i, engine: 'behavioral', type: 'persona_injection', score: 25 },
    { regex: /(?:api[_\s]?key|password|secret|ssn|credit.?card)/i, engine: 'pii', type: 'credential_exposure', score: 30 },
  ];

  const details: any[] = [];
  let score = 0;

  for (const pattern of patterns) {
    if (pattern.regex.test(text)) {
      score += pattern.score;
      details.push({
        engine: pattern.engine,
        threat_type: pattern.type,
        confidence: 0.75 + Math.random() * 0.2,
        description: `Detected ${pattern.type.replace(/_/g, ' ')} pattern`,
      });
    }
  }

  score = Math.min(100, score);
  const riskLevel = score >= 80 ? 'critical' : score >= 60 ? 'high' : score >= 30 ? 'medium' : 'low';

  return {
    is_safe: score < 50,
    risk_score: score,
    risk_level: riskLevel,
    verdict: score >= 50 ? 'BLOCKED' : 'ALLOWED',
    engines_triggered: details.map(d => d.engine),
    processing_time_ms: Math.floor(50 + Math.random() * 100),
    latency_ms: Math.floor(50 + Math.random() * 100),
    details,
    detections: details, // backward compat
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
      const timeout = getTimeout();
      console.log(`[BRAIN] Calling: ${url} (timeout: ${timeout}ms, warmed: ${isWarmedUp})`);
      
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(brainPayload),
        signal: AbortSignal.timeout(timeout),
      });
      
      console.log(`[BRAIN] Response status: ${res.status}`);
      
      if (res.ok) {
        const data = await res.json();
        isWarmedUp = true; // Mark as warmed up after first success
        console.log(`[BRAIN] Success, risk_score: ${data.risk_score}, now warmed up`);
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
  } catch (_error) {
    console.error('[BRAIN] Fatal error:', _error);
    return NextResponse.json(
      { error: 'Failed to analyze' },
      { status: 500 }
    );
  }
}
