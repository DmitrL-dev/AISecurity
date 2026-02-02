/**
 * Login Button Component
 */
"use client";

import { signIn, signOut, useSession } from "next-auth/react";
import { LogIn, LogOut, Loader2 } from "lucide-react";

export function LoginButton() {
  const { data: session, status } = useSession();

  if (status === "loading") {
    return (
      <button
        disabled
        className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-700 text-gray-400"
      >
        <Loader2 className="h-4 w-4 animate-spin" />
        <span>Loading...</span>
      </button>
    );
  }

  if (session) {
    return (
      <button
        onClick={() => signOut({ callbackUrl: "/" })}
        className="flex items-center gap-2 px-4 py-2 rounded-lg bg-red-600/10 text-red-400 hover:bg-red-600/20 transition-colors"
      >
        <LogOut className="h-4 w-4" />
        <span>Logout</span>
      </button>
    );
  }

  return (
    <button
      onClick={() => signIn("keycloak")}
      className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition-colors"
    >
      <LogIn className="h-4 w-4" />
      <span>Login</span>
    </button>
  );
}
