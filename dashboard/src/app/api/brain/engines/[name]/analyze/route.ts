import { NextResponse } from 'next/server';
import { BRAIN_API_URL } from '@/lib/brain-api';

interface Params {
  params: Promise<{ name: string }>;
}

interface AnalyzeRequest {
  content: string;
  analysis_type?: string;
  include_mitre?: boolean;
}

/**
 * POST /api/brain/engines/[name]/analyze
 * Run analysis with specific engine
 */
export async function POST(req: Request, { params }: Params) {
  try {
    const { name } = await params;
    const body: AnalyzeRequest = await req.json();

    if (!body.content) {
      return NextResponse.json(
        { error: 'Content is required' },
        { status: 400 }
      );
    }

    // Map engine names to BRAIN API endpoints
    const engineEndpoints: Record<string, string> = {
      'qwen-guard': '/v1/analyze/safety',
      'foundation-sec': '/v1/analyze/reasoning',
    };

    const endpoint = engineEndpoints[name];
    if (!endpoint) {
      return NextResponse.json(
        { error: `Unknown engine: ${name}` },
        { status: 404 }
      );
    }

    // Try to call BRAIN API
    try {
      const res = await fetch(`${BRAIN_API_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(30000),
      });

      if (res.ok) {
        const data = await res.json();
        return NextResponse.json(data);
      }
    } catch {
      // BRAIN API not available, return mock data
    }

    // Mock responses for development
    if (name === 'qwen-guard') {
      const isSafe = !body.content.toLowerCase().includes('attack');
      return NextResponse.json({
        engine: 'qwen-guard',
        result: {
          level: isSafe ? 'safe' : 'unsafe',
          categories: isSafe ? [] : ['Jailbreak'],
          refusal: false,
          risk_score: isSafe ? 0 : 85,
        },
        latency_ms: 125,
      });
    }

    if (name === 'foundation-sec') {
      return NextResponse.json({
        engine: 'foundation-sec',
        result: {
          analysis_type: body.analysis_type || 'threat_model',
          reasoning: {
            thinking: `Analyzing the input for security implications...\n\nThe content appears to contain references to system configurations that could be exploited.\n\nKey observations:\n1. Potential injection vectors identified\n2. Insufficient input validation\n3. Missing access controls`,
            conclusion: 'Medium-high risk detected. Input contains patterns associated with command injection attempts. Recommend implementing strict input validation and parameterized queries.',
            confidence: 0.78,
          },
          mitre_mappings: body.include_mitre !== false ? [
            {
              technique_id: 'T1059',
              technique_name: 'Command and Scripting Interpreter',
              tactic: 'Execution',
              confidence: 0.85,
            },
            {
              technique_id: 'T1190',
              technique_name: 'Exploit Public-Facing Application',
              tactic: 'Initial Access',
              confidence: 0.72,
            },
          ] : [],
          risk_score: 65,
          recommendations: [
            'Implement input validation using allowlists',
            'Use parameterized queries for database operations',
            'Enable WAF rules for injection detection',
          ],
        },
        latency_ms: 3250,
      });
    }

    return NextResponse.json(
      { error: `Unknown engine: ${name}` },
      { status: 404 }
    );
  } catch (error) {
    console.error('Engine analyze error:', error);
    return NextResponse.json(
      { error: 'Analysis failed' },
      { status: 500 }
    );
  }
}
