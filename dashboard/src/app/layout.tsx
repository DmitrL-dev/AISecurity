"use client";

import "./globals.css";
import { Sidebar, SidebarProvider } from "@/components/Sidebar";
import { Header } from "@/components/Header";
import { ToastProvider } from "@/components/Toast";
import { LiveThreatsProvider } from "@/lib/live-threats";
import { AuthProvider } from "@/components/auth";
import { usePathname } from "next/navigation";
import CDNStatusBanner from "@/components/CDNStatusBanner";

// Routes without sidebar
const publicRoutes = ["/login", "/unauthorized"];

function LayoutContent({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isPublicPage = publicRoutes.some(route => pathname?.startsWith(route));

  if (isPublicPage) {
    return <>{children}</>;
  }

  return (
    <LiveThreatsProvider>
      <SidebarProvider>
        <div className="flex h-screen">
          <Sidebar />
          <div className="flex-1 flex flex-col overflow-hidden min-w-0">
            <Header />
            <main className="flex-1 overflow-auto p-4 lg:p-6">{children}</main>
          </div>
        </div>
      </SidebarProvider>
    </LiveThreatsProvider>
  );
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <title>SENTINEL | AI Security Platform</title>
        <meta name="description" content="Enterprise AI Security Operations Center" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body className="bg-[#0a0e1a] text-white min-h-screen">
        <AuthProvider>
          <ToastProvider>
            <LayoutContent>{children}</LayoutContent>
            <CDNStatusBanner />
          </ToastProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
