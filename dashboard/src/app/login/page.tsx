/**
 * Login Page
 */
"use client";

import { signIn } from "next-auth/react";
import { useSearchParams } from "next/navigation";
import { Shield, LogIn } from "lucide-react";
import { Suspense, useState } from "react";

function LoginContent() {
  const searchParams = useSearchParams();
  const callbackUrl = searchParams.get("callbackUrl") || "/";
  const error = searchParams.get("error");
  const [email, setEmail] = useState("admin@sentinel.dev");
  const [password, setPassword] = useState("dev");
  const [loading, setLoading] = useState(false);

  // Dev mode login handler
  const handleDevLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    await signIn("credentials", { email, password, callbackUrl });
  };

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <div className="max-w-md w-full space-y-8">
        {/* Logo */}
        <div className="text-center">
          <div className="flex justify-center">
            <div className="w-16 h-16 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
              <Shield className="h-8 w-8 text-white" />
            </div>
          </div>
          <h1 className="mt-4 text-3xl font-bold text-white">SENTINEL</h1>
          <p className="mt-2 text-gray-400">AI Security Platform</p>
        </div>

        {/* Error message */}
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 text-red-400 text-sm">
            {error === "OAuthSignin" && "Error starting sign in process"}
            {error === "OAuthCallback" && "Error during authentication callback"}
            {error === "SessionRequired" && "Please sign in to continue"}
            {error === "CredentialsSignin" && "Invalid credentials"}
            {error === "Default" && "An error occurred during sign in"}
          </div>
        )}

        {/* Login card */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-8">
          <h2 className="text-xl font-semibold text-white mb-6">
            Sign in to your account
          </h2>

          {/* Dev mode form */}
          <form onSubmit={handleDevLogin} className="space-y-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-purple-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-purple-500 focus:outline-none"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-3 px-4 py-3 bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white rounded-lg transition-colors font-medium"
            >
              <LogIn className="h-5 w-5" />
              {loading ? "Signing in..." : "Sign in (Dev Mode)"}
            </button>
          </form>

          <p className="mt-6 text-yellow-500/70 text-xs text-center">
            ⚠️ Dev mode — any credentials accepted
          </p>
        </div>

        {/* Footer */}
        <p className="text-center text-gray-600 text-sm">
          Protected by SENTINEL Security
        </p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-gray-400">Loading...</div>
      </div>
    }>
      <LoginContent />
    </Suspense>
  );
}
