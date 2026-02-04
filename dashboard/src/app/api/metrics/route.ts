import { NextResponse } from 'next/server';
import { BRAIN_API_URL } from '@/lib/brain-api';

const SHIELD_URL = process.env.SHIELD_URL || 'http://localhost:8081';
const STRIKE_URL = process.env.STRIKE_URL || 'http://localhost:8001';

export async function GET() {
  try {
    // === Fetch Shield Stats ===
    let shieldStats = {
      requests: { total: 0, allowed: 0, blocked: 0, warned: 0 },
      block_rate_percent: 0,
      avg_latency_ms: 0,
      uptime_seconds: 0,
    };
    let shieldOnline = false;
    
    try {
      const shieldRes = await fetch(`${SHIELD_URL}/stats`, { cache: 'no-store' });
      if (shieldRes.ok) {
        shieldStats = await shieldRes.json();
        shieldOnline = true;
      }
    } catch {
      // Shield not available
    }

    // === Fetch BRAIN Health ===
    let brainStatus = 'unknown';
    let brainVersion = '?.?.?';
    
    try {
      const healthRes = await fetch(`${BRAIN_API_URL}/health`, { cache: 'no-store' });
      if (healthRes.ok) {
        const health = await healthRes.json();
        brainStatus = health.status;
        brainVersion = health.version;
      }
    } catch {
      // BRAIN not available
    }

    // === Fetch BRAIN Engines ===
    let engineCount = { active: 0, total: 0 };
    try {
      const enginesRes = await fetch(`${BRAIN_API_URL}/v1/engines`, { cache: 'no-store' });
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

    // === Fetch Shield Guards ===
    let enabledGuards = 0;
    let totalGuards = 0;
    try {
      const guardsRes = await fetch(`${SHIELD_URL}/guards`, { cache: 'no-store' });
      if (guardsRes.ok) {
        const guards = await guardsRes.json();
        const guardEntries = Object.values(guards) as { enabled: boolean }[];
        totalGuards = guardEntries.length;
        enabledGuards = guardEntries.filter(g => g.enabled).length;
      }
    } catch {
      // Shield guards not available
    }

    // === Fetch Strike Payloads ===
    let strikePayloads = { llm_vectors: 0, jailbreaks: 0, web_payloads: 0, total: 0 };
    try {
      const strikeRes = await fetch(`${STRIKE_URL}/`, { cache: 'no-store' });
      if (strikeRes.ok) {
        const strikeData = await strikeRes.json();
        if (strikeData.payloads) {
          strikePayloads = strikeData.payloads;
        }
      }
    } catch {
      // Strike not available
    }

    // === Fetch Shield History for recent threats ===
    let recentThreats: any[] = [];
    try {
      const historyRes = await fetch(`${SHIELD_URL}/history`, { cache: 'no-store' });
      if (historyRes.ok) {
        const history = await historyRes.json();
        recentThreats = (history || [])
          .filter((h: any) => h.verdict === 'block' || h.verdict === 'warn')
          .slice(0, 5)
          .map((h: any, i: number) => ({
            id: `T${String(i + 1).padStart(3, '0')}`,
            type: h.threats?.[0] || h.matched_rule || 'Unknown',
            severity: h.verdict === 'block' ? 'critical' : 'high',
            timestamp: h.timestamp * 1000,
            text_preview: h.text_preview,
          }));
      }
    } catch {
      // No history
    }

    // === Calculate Real Metrics ===
    const totalRequests = shieldStats.requests?.total || 0;
    const blockedRequests = shieldStats.requests?.blocked || 0;
    const warnedRequests = shieldStats.requests?.warned || 0;
    
    // Breakdown by threat type (from history)
    const threatBreakdown = {
      promptInjection: { count: 0, percentage: 0 },
      jailbreaks: { count: 0, percentage: 0 },
      dataExfiltration: { count: 0, percentage: 0 },
      mcpAttacks: { count: 0, percentage: 0 },
      other: { count: 0, percentage: 0 },
    };

    // Count threats by type from recent history
    recentThreats.forEach(t => {
      const type = t.type.toLowerCase();
      if (type.includes('injection') || type.includes('prompt')) {
        threatBreakdown.promptInjection.count++;
      } else if (type.includes('jailbreak') || type.includes('dan')) {
        threatBreakdown.jailbreaks.count++;
      } else if (type.includes('exfil') || type.includes('data')) {
        threatBreakdown.dataExfiltration.count++;
      } else if (type.includes('mcp') || type.includes('tool')) {
        threatBreakdown.mcpAttacks.count++;
      } else {
        threatBreakdown.other.count++;
      }
    });

    // Calculate percentages
    const totalThreats = Object.values(threatBreakdown).reduce((sum, t) => sum + t.count, 0);
    if (totalThreats > 0) {
      Object.keys(threatBreakdown).forEach(key => {
        const k = key as keyof typeof threatBreakdown;
        threatBreakdown[k].percentage = Math.round((threatBreakdown[k].count / totalThreats) * 1000) / 10;
      });
    }

    return NextResponse.json({
      payloads: {
        total: strikePayloads.total || totalRequests, // Strike payloads first, fallback to requests
        today: strikePayloads.total || totalRequests,
        trend: strikePayloads.total > 0 ? 12 : 0,
        breakdown: strikePayloads, // Include breakdown
      },
      threats: {
        blocked: blockedRequests,
        warned: warnedRequests,
        today: blockedRequests,
        trend: 0,
      },
      engines: engineCount,
      guards: {
        active: enabledGuards,
        total: totalGuards,
      },
      apiCalls: {
        total: totalRequests,
        today: totalRequests,
        trend: 0,
      },
      shield: {
        status: shieldOnline ? 'online' : 'offline',
        block_rate: shieldStats.block_rate_percent || 0,
        avg_latency: shieldStats.avg_latency_ms || 0,
        uptime: shieldStats.uptime_seconds || 0,
      },
      brain: {
        status: brainStatus,
        version: brainVersion,
      },
      breakdown: threatBreakdown,
      recentThreats,
      timestamp: Date.now(),
    });
  } catch (_error) {
    return NextResponse.json(
      { error: 'Failed to fetch metrics' },
      { status: 500 }
    );
  }
}
