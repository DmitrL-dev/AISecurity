/**
 * SENTINEL Dashboard Middleware
 * 
 * Handles authentication and RBAC for all routes
 */

import { NextResponse } from "next/server";
import type { NextRequest as _NextRequest } from "next/server";
import { auth } from "@/lib/auth";
import { canAccess, isPublicRoute } from "@/lib/rbac";

export default auth((req) => {
  const { pathname } = req.nextUrl;
  
  // Debug logging
  console.log(`[Middleware] ${pathname} - auth:`, req.auth ? 'YES' : 'NO', req.auth?.user?.email || '');
  
  // Allow public routes
  if (isPublicRoute(pathname)) {
    return NextResponse.next();
  }
  
  // Check if user is authenticated
  if (!req.auth) {
    // Redirect to login with callback URL
    const loginUrl = new URL("/login", req.url);
    loginUrl.searchParams.set("callbackUrl", pathname);
    return NextResponse.redirect(loginUrl);
  }
  
  // Get user roles from session
  const session = req.auth as { roles?: string[] };
  const roles = session.roles || [];
  
  // Check RBAC permissions
  if (!canAccess(roles, pathname)) {
    // User is authenticated but lacks permission
    return NextResponse.redirect(new URL("/unauthorized", req.url));
  }
  
  // All checks passed
  return NextResponse.next();
});

export const config = {
  // Match all routes except static files and images
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.png$|.*\\.jpg$|.*\\.svg$).*)",
  ],
};
