/**
 * Role Guard Component
 * 
 * Conditionally render children based on user roles
 */
"use client";

import { useSession } from "next-auth/react";
import { ReactNode } from "react";

interface RoleGuardProps {
  /** Required roles (any of these) */
  roles: string[];
  /** Content to render if user has required role */
  children: ReactNode;
  /** Optional fallback content */
  fallback?: ReactNode;
  /** Show loading state while checking */
  showLoading?: boolean;
}

export function RoleGuard({
  roles,
  children,
  fallback = null,
  showLoading = false,
}: RoleGuardProps) {
  const { data: session, status } = useSession();

  if (status === "loading" && showLoading) {
    return (
      <div className="animate-pulse bg-gray-700 rounded h-8 w-24" />
    );
  }

  // Get session roles
  const sessionWithRoles = session as { roles?: string[] } | null;
  const userRoles = sessionWithRoles?.roles || [];

  // Check if user has any of the required roles
  const hasRole = roles.some((role) => userRoles.includes(role));

  if (!hasRole) {
    return <>{fallback}</>;
  }

  return <>{children}</>;
}

/**
 * Admin-only guard
 */
export function AdminOnly({
  children,
  fallback,
}: {
  children: ReactNode;
  fallback?: ReactNode;
}) {
  return (
    <RoleGuard roles={["admin"]} fallback={fallback}>
      {children}
    </RoleGuard>
  );
}

/**
 * Analyst or admin guard
 */
export function AnalystOnly({
  children,
  fallback,
}: {
  children: ReactNode;
  fallback?: ReactNode;
}) {
  return (
    <RoleGuard roles={["admin", "analyst"]} fallback={fallback}>
      {children}
    </RoleGuard>
  );
}
