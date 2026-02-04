import { NextResponse } from 'next/server';
import { BRAIN_API_URL } from '@/lib/brain-api';

interface Params {
  params: Promise<{ name: string }>;
}

/**
 * GET /api/brain/engines/[name]/stats
 * Get engine statistics
 */
export async function GET(req: Request, { params }: Params) {
  try {
    const { name } = await params;

    // Map engine names to BRAIN API endpoints
    const engineEndpoints: Record<string, string> = {
      'qwen-guard': '/v1/engines/qwen-guard/metrics',
      'foundation-sec': '/v1/engines/foundation-sec/metrics',
    };

    const endpoint = engineEndpoints[name];
    if (!endpoint) {
      return NextResponse.json(
        { error: `Unknown engine: ${name}` },
        { status: 404 }
      );
    }

    // Try to fetch from BRAIN API
    try {
      const res = await fetch(`${BRAIN_API_URL}${endpoint}`, {
        cache: 'no-store',
        signal: AbortSignal.timeout(5000),
      });

      if (res.ok) {
        const data = await res.json();
        return NextResponse.json(data);
      }
    } catch {
      // BRAIN API not available, return mock data
    }

    // Mock data for development
    if (name === 'qwen-guard') {
      return NextResponse.json({
        engine: 'qwen-guard',
        status: 'healthy',
        mode: 'api',
        model: 'Qwen/Qwen3Guard-Gen-0.6B',
        metrics: {
          call_count: 1234,
          error_count: 12,
          avg_latency_ms: 125.5,
          categories: {
            safe: 980,
            controversial: 142,
            unsafe: 112,
          },
          category_breakdown: {
            Violent: 45,
            'Non-violent Illegal Acts': 23,
            'Sexual Content': 12,
            PII: 8,
            'Suicide & Self-Harm': 5,
            'Unethical Acts': 7,
            'Politically Sensitive': 3,
            'Copyright Violation': 2,
            Jailbreak: 7,
          },
        },
      });
    }

    if (name === 'foundation-sec') {
      return NextResponse.json({
        engine: 'foundation-sec',
        status: 'loading',
        mode: 'api',
        model: 'fdtn-ai/Foundation-Sec-8B-Reasoning',
        metrics: {
          call_count: 45,
          error_count: 2,
          avg_latency_ms: 3250.0,
          analysis_types: {
            threat_model: 15,
            attack_path: 12,
            vulnerability: 10,
            risk_assessment: 5,
            configuration: 2,
            incident: 1,
          },
          mitre_techniques_found: 87,
          avg_risk_score: 62.5,
        },
      });
    }

    return NextResponse.json(
      { error: `Unknown engine: ${name}` },
      { status: 404 }
    );
  } catch (_error) {
    console.error('Engine stats error:', _error);
    return NextResponse.json(
      { error: 'Failed to get engine stats' },
      { status: 500 }
    );
  }
}
