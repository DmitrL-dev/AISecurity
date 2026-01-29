import { NextResponse } from 'next/server';
import { BRAIN_API_URL } from '@/lib/brain-api';

// Mock metrics for now - will be replaced with real BRAIN data
const mockMetrics = {
  payloads: {
    total: 39847,
    today: 127,
    trend: 12,
  },
  threats: {
    blocked: 1247,
    today: 23,
    trend: -8,
  },
  engines: {
    active: 7,
    total: 7,
  },
  apiCalls: {
    total: 4200,
    today: 312,
    trend: 23,
  },
  breakdown: {
    promptInjection: { count: 181, percentage: 48.3 },
    jailbreaks: { count: 55, percentage: 14.7 },
    dataExfiltration: { count: 46, percentage: 12.2 },
    mcpAttacks: { count: 41, percentage: 10.9 },
    other: { count: 52, percentage: 13.9 },
  },
  recentThreats: [
    { id: 'T001', type: 'Prompt Injection', severity: 'critical', timestamp: Date.now() - 120000 },
    { id: 'T002', type: 'Jailbreak Attempt', severity: 'high', timestamp: Date.now() - 900000 },
    { id: 'T003', type: 'PII Leakage', severity: 'high', timestamp: Date.now() - 3600000 },
  ],
};

export async function GET() {
  try {
    // Try to get real health data from BRAIN
    let brainStatus = 'unknown';
    let brainVersion = '?.?.?';
    
    try {
      const healthRes = await fetch(`${BRAIN_API_URL}/health`, {
        cache: 'no-store',
      });
      if (healthRes.ok) {
        const health = await healthRes.json();
        brainStatus = health.status;
        brainVersion = health.version;
      }
    } catch {
      // BRAIN not available
    }

    // Try to get engines
    let engineCount = { active: 7, total: 7 };
    try {
      const enginesRes = await fetch(`${BRAIN_API_URL}/v1/engines`, {
        cache: 'no-store',
      });
      if (enginesRes.ok) {
        const engines = await enginesRes.json();
        const engineList = Array.isArray(engines) ? engines : engines.engines || [];
        engineCount = {
          active: engineList.filter((e: any) => e.enabled).length,
          total: engineList.length,
        };
      }
    } catch {
      // Use default
    }

    return NextResponse.json({
      ...mockMetrics,
      engines: engineCount,
      brain: {
        status: brainStatus,
        version: brainVersion,
      },
      timestamp: Date.now(),
    });
  } catch (error) {
    return NextResponse.json(
      { error: 'Failed to fetch metrics' },
      { status: 500 }
    );
  }
}
