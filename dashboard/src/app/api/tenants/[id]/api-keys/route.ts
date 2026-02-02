/**
 * API Keys Management
 *
 * GET /api/tenants/[id]/api-keys - List API keys
 * POST /api/tenants/[id]/api-keys - Create new key
 */

import { NextResponse } from "next/server";
import { db } from "@/db";
import { tenantApiKeys } from "@/db/schema";
import { eq } from "drizzle-orm";
import { createApiKey, revokeApiKey } from "@/lib/api-key-auth";

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

    const keys = await db
      .select({
        id: tenantApiKeys.id,
        name: tenantApiKeys.name,
        keyPrefix: tenantApiKeys.keyPrefix,
        scopes: tenantApiKeys.scopes,
        rateLimit: tenantApiKeys.rateLimit,
        isActive: tenantApiKeys.isActive,
        lastUsedAt: tenantApiKeys.lastUsedAt,
        expiresAt: tenantApiKeys.expiresAt,
        createdAt: tenantApiKeys.createdAt,
      })
      .from(tenantApiKeys)
      .where(eq(tenantApiKeys.tenantId, tenantId));

    return NextResponse.json({ keys });
  } catch (error) {
    console.error("Failed to list API keys:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

export async function POST(req: Request, { params }: Params) {
  try {
    const { id: tenantId } = await params;
    const body = await req.json();
    const { name, scopes, rateLimit, expiresAt } = body;

    if (!name) {
      return NextResponse.json(
        { error: "Name is required" },
        { status: 400 }
      );
    }

    const result = await createApiKey(tenantId, name, {
      scopes,
      rateLimit,
      expiresAt: expiresAt ? new Date(expiresAt) : undefined,
    });

    return NextResponse.json(
      {
        id: result.id,
        key: result.key, // Only shown once!
        message: "Save this key - it won't be shown again",
      },
      { status: 201 }
    );
  } catch (error) {
    console.error("Failed to create API key:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}

export async function DELETE(req: Request, { params }: Params) {
  try {
    const url = new URL(req.url);
    const keyId = url.searchParams.get("keyId");

    if (!keyId) {
      return NextResponse.json(
        { error: "keyId is required" },
        { status: 400 }
      );
    }

    await revokeApiKey(keyId);

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("Failed to revoke API key:", error);
    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
