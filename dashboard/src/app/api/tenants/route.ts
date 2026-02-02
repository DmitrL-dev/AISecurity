/**
 * Tenants API
 *
 * GET /api/tenants - List user's tenants
 * POST /api/tenants - Create new tenant
 */

import { NextResponse } from "next/server";
import { db } from "@/db";
import { tenants, tenantMembers } from "@/db/schema";
import { eq } from "drizzle-orm";

export async function GET(req: Request) {
  try {
    // TODO: Get user from session
    const userId = req.headers.get("X-User-Id");

    if (!userId) {
      return NextResponse.json(
        { error: "Unauthorized" },
        { status: 401 }
      );
    }

    if (!db) {
      return NextResponse.json(
        { error: "Database not configured" },
        { status: 500 }
      );
    }

    // Get tenants where user is a member
    const userTenants = await db
      .select({
        id: tenants.id,
        name: tenants.name,
        slug: tenants.slug,
        plan: tenants.plan,
        isActive: tenants.isActive,
        role: tenantMembers.role,
      })
      .from(tenants)
      .innerJoin(
        tenantMembers,
        eq(tenants.id, tenantMembers.tenantId)
      )
      .where(eq(tenantMembers.userId, userId));

    return NextResponse.json({ tenants: userTenants });
  } catch (error) {
    console.error("Failed to list tenants:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

export async function POST(req: Request) {
  try {
    const userId = req.headers.get("X-User-Id");

    if (!userId) {
      return NextResponse.json(
        { error: "Unauthorized" },
        { status: 401 }
      );
    }

    const body = await req.json();
    const { name, slug } = body;

    if (!name || !slug) {
      return NextResponse.json(
        { error: "Name and slug are required" },
        { status: 400 }
      );
    }

    if (!db) {
      return NextResponse.json(
        { error: "Database not configured" },
        { status: 500 }
      );
    }

    // Create tenant
    const [newTenant] = await db
      .insert(tenants)
      .values({
        name,
        slug: slug.toLowerCase().replace(/[^a-z0-9-]/g, "-"),
        plan: "community",
      })
      .returning();

    // Add creator as owner
    await db.insert(tenantMembers).values({
      tenantId: newTenant.id,
      userId,
      role: "owner",
      acceptedAt: new Date(),
    });

    return NextResponse.json({ tenant: newTenant }, { status: 201 });
  } catch (error: any) {
    if (error?.code === "23505") {
      // Unique violation
      return NextResponse.json(
        { error: "Slug already exists" },
        { status: 409 }
      );
    }
    console.error("Failed to create tenant:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
