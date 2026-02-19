"use client";

import { useState } from "react";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { FooterGuidance } from "./FooterGuidance";
import { AIAssistantPanel } from "../ai/AIAssistantPanel";
import { MobileBottomNav } from "./MobileBottomNav";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="h-screen flex flex-col bg-background text-foreground">
      <Topbar onOpenMobile={() => setMobileOpen(true)} />

      <div className="flex flex-1 min-h-0">
        {/* Desktop sidebar — fixed, not collapsible */}
        <div className="hidden lg:block">
          <Sidebar />
        </div>

        {/* Mobile sidebar overlay */}
        {mobileOpen && (
          <div className="lg:hidden fixed inset-0 z-50">
            <div
              className="absolute inset-0 bg-black/50"
              onClick={() => setMobileOpen(false)}
            />
            <div className="absolute left-0 top-0 h-full">
              <Sidebar onNavigate={() => setMobileOpen(false)} />
            </div>
          </div>
        )}

        {/* Scrollable content area */}
        <main className="flex-1 min-w-0 overflow-auto px-3 py-3 sm:px-4 sm:py-4 pb-20 lg:pb-4">
          {children}
        </main>
      </div>

      {/* Desktop footer */}
      <div className="hidden lg:block">
        <FooterGuidance />
      </div>

      {/* Mobile bottom nav */}
      <MobileBottomNav />

      <AIAssistantPanel />
    </div>
  );
}

export default AppShell;
