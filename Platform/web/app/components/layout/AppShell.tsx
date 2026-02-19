"use client";

import { useEffect, useState } from "react";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { FooterGuidance } from "./FooterGuidance";
import { AIAssistantPanel } from "../ai/AIAssistantPanel";

const LS_KEY = "bt_sidebar_collapsed";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    try {
      const v = localStorage.getItem(LS_KEY);
      if (v === "1") setCollapsed(true);
    } catch {}
  }, []);

  function toggleCollapse() {
    setCollapsed((v) => {
      const next = !v;
      try {
        localStorage.setItem(LS_KEY, next ? "1" : "0");
      } catch {}
      return next;
    });
  }

  return (
    <div className="h-screen flex flex-col bg-background text-foreground">
      <Topbar onOpenMobile={() => setMobileOpen(true)} />

      <div className="flex flex-1 min-h-0">
        {/* Desktop sidebar */}
        <div className="hidden md:block relative">
          <Sidebar collapsed={collapsed} onToggleCollapse={toggleCollapse} />
        </div>

        {/* Mobile sidebar overlay */}
        {mobileOpen && (
          <div className="md:hidden fixed inset-0 z-50">
            <div
              className="absolute inset-0 bg-black/50"
              onClick={() => setMobileOpen(false)}
            />
            <div className="absolute left-0 top-0 h-full">
              <Sidebar
                collapsed={false}
                onToggleCollapse={() => {}}
                onNavigate={() => setMobileOpen(false)}
              />
            </div>
          </div>
        )}

        {/* Scrollable content area */}
        <main className="flex-1 min-w-0 overflow-auto px-4 py-4">{children}</main>
      </div>

      <FooterGuidance />
      <AIAssistantPanel />
    </div>
  );
}

export default AppShell;
