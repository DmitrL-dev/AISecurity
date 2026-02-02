/**
 * Usage API
 *
 * GET /api/tenants/[id]/usage - Get tenant usage stats
 */

import { NextResponse } from "next/server";
import { db } from "@/db";
import { usageMetrics, tenants } from "@/db/schema";
import { eq, and, gte, sql } from "drizzle-orm";
import { PLAN_LIMITS, type PlanType } from "@/lib/plan-limits";

interface Params {
  params: Promise<{ id: string }>;
}

export async function GET(req: Request, { params }: Params) {
  try {
    const { id: tenantId } = await params;

    if (!db) {
      return NextResponse.json(
        { error: "Database not configured" },
        { status: 500 }
      );
    }

    // Get tenant info
    const [tenant] = await db
      .select({
        id: tenants.id,
        name: tenants.name,
        plan: tenants.plan,
      })
      .from(tenants)
      .where(eq(tenants.id, tenantId))
      .limit(1);

    if (!tenant) {
      return NextResponse.json(
        { error: "Tenant not found" },
        { status: 404 }
      );
    }

    // Get current month start
    const now = new Date();
    const monthStart = new Date(now.getFullYear(), now.getMonth(), 1)
      .toISOString()
      .split("T")[0];

    // Aggregate usage for current month
    const [usage] = await db
      .select({
        totalApiCalls: sql<number>`COALESCE(SUM(${usageMetrics.apiCalls}), 0)`,
        totalAnalyses: sql<number>`COALESCE(SUM(${usageMetrics.analyses}), 0)`,
        totalBlocked: sql<number>`COALESCE(SUM(${usageMetrics.blockedThreats}), 0)`,
      })
      .from(usageMetrics)
      .where(
        and(
          eq(usageMetrics.tenantId, tenantId),
          gte(usageMetrics.date, monthStart)
        )
      );

    // Get plan limits
    const plan = (tenant.plan || "community") as PlanType;
    const limits = PLAN_LIMITS[plan];

    return NextResponse.json({
      tenant: {
        id: tenant.id,
        name: tenant.name,
        plan,
      },
      usage: {
        apiCalls: Number(usage.totalApiCalls),
        analyses: Number(usage.totalAnalyses),
        blockedThreats: Number(usage.totalBlocked),
      },
      limits: {
        analysesPerMonth: limits.analysesPerMonth,
        remaining: Math.max(
          0,
          limits.analysesPerMonth - Number(usage.totalAnalyses)
        ),
      },
      period: {
        start: monthStart,
        end: new Date(now.getFullYear(), now.getMonth() + 1, 0)
          .toISOString()
          .split("T")[0],
      },
    });
  } catch (error) {
    console.error("Failed to get usage:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
