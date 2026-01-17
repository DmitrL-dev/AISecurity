import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "SENTINEL Dashboard",
  description: "AI Security Operations Center",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="flex min-h-screen">
          <aside className="w-64 bg-[#111] border-r border-[#2a2a2a] p-4">
            <div className="text-xl font-bold text-emerald-500 mb-8">
              🛡️ SENTINEL
            </div>
            <nav className="space-y-2">
              <a href="/" className="block px-4 py-2 rounded hover:bg-[#1a1a1a]">
                Dashboard
              </a>
              <a href="/analyze" className="block px-4 py-2 rounded hover:bg-[#1a1a1a]">
                Analyze
              </a>
              <a href="/engines" className="block px-4 py-2 rounded hover:bg-[#1a1a1a]">
                Engines
              </a>
              <a href="/settings" className="block px-4 py-2 rounded hover:bg-[#1a1a1a]">
                Settings
              </a>
            </nav>
          </aside>
          <main className="flex-1 p-8">{children}</main>
        </div>
      </body>
    </html>
  );
}
