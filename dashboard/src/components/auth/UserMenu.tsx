/**
 * User Menu Component
 * 
 * Displays user info and role in header
 */
"use client";

import { useSession, signOut } from "next-auth/react";
import { useState } from "react";
import { 
  User, 
  LogOut, 
  Settings, 
  Shield, 
  ChevronDown,
  Loader2 
} from "lucide-react";

const roleColors: Record<string, string> = {
  admin: "bg-red-500/20 text-red-400",
  analyst: "bg-blue-500/20 text-blue-400",
  viewer: "bg-gray-500/20 text-gray-400",
  "api-only": "bg-purple-500/20 text-purple-400",
};

export function UserMenu() {
  const { data: session, status } = useSession();
  const [isOpen, setIsOpen] = useState(false);

  if (status === "loading") {
    return (
      <div className="flex items-center gap-2 text-gray-400">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span className="text-sm">Loading...</span>
      </div>
    );
  }

  if (!session) {
    return null;
  }

  // Get roles from session
  const sessionWithRoles = session as { roles?: string[]; user?: { email?: string; name?: string } };
  const roles = sessionWithRoles.roles || [];
  const primaryRole = roles[0] || "viewer";
  const email = sessionWithRoles.user?.email || "unknown";
  const name = sessionWithRoles.user?.name || email.split("@")[0];

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-gray-800 transition-colors"
      >
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center">
            <User className="h-4 w-4 text-white" />
          </div>
          <div className="text-left hidden sm:block">
            <div className="text-sm font-medium text-white">{name}</div>
            <div className={`text-xs px-2 py-0.5 rounded ${roleColors[primaryRole] || roleColors.viewer}`}>
              {primaryRole}
            </div>
          </div>
        </div>
        <ChevronDown className={`h-4 w-4 text-gray-400 transition-transform ${isOpen ? "rotate-180" : ""}`} />
      </button>

      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />

          {/* Dropdown */}
          <div className="absolute right-0 mt-2 w-56 bg-gray-900 border border-gray-700 rounded-lg shadow-lg z-20">
            {/* User info */}
            <div className="px-4 py-3 border-b border-gray-700">
              <div className="text-sm font-medium text-white">{name}</div>
              <div className="text-xs text-gray-400">{email}</div>
              <div className="flex gap-1 mt-2">
                {roles.map((role) => (
                  <span
                    key={role}
                    className={`text-xs px-2 py-0.5 rounded ${roleColors[role] || roleColors.viewer}`}
                  >
                    {role}
                  </span>
                ))}
              </div>
            </div>

            {/* Menu items */}
            <div className="py-1">
              <button
                onClick={() => {
                  setIsOpen(false);
                  // Navigate to profile
                }}
                className="w-full flex items-center gap-2 px-4 py-2 text-sm text-gray-300 hover:bg-gray-800"
              >
                <User className="h-4 w-4" />
                Profile
              </button>

              <button
                onClick={() => {
                  setIsOpen(false);
                  // Navigate to settings
                }}
                className="w-full flex items-center gap-2 px-4 py-2 text-sm text-gray-300 hover:bg-gray-800"
              >
                <Settings className="h-4 w-4" />
                Settings
              </button>

              {roles.includes("admin") && (
                <button
                  onClick={() => {
                    setIsOpen(false);
                    // Navigate to admin
                  }}
                  className="w-full flex items-center gap-2 px-4 py-2 text-sm text-gray-300 hover:bg-gray-800"
                >
                  <Shield className="h-4 w-4" />
                  Admin Panel
                </button>
              )}
            </div>

            {/* Logout */}
            <div className="border-t border-gray-700 py-1">
              <button
                onClick={() => signOut({ callbackUrl: "/" })}
                className="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-400 hover:bg-gray-800"
              >
                <LogOut className="h-4 w-4" />
                Logout
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
