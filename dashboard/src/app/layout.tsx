import type { Metadata } from "next";
import "./globals.css";
import { Sidebar, SidebarProvider } from "@/components/Sidebar";
import { Header } from "@/components/Header";
import { ToastProvider } from "@/components/Toast";
import { LiveThreatsProvider } from "@/lib/live-threats";

export const metadata: Metadata = {
  title: "SENTINEL | AI Security Platform",
  description: "Enterprise AI Security Operations Center",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </head>
      <body className="bg-[#0a0e1a] text-white min-h-screen">
        <ToastProvider>
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
        </ToastProvider>
      </body>
    </html>
  );
}
