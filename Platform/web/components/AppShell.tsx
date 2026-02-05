"use client";

import * as React from "react";
import Sidebar from "./sidebar";
import Header from "./header";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = React.useState(false);
  const [mobileOpen, setMobileOpen] = React.useState(false);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="flex">
        <Sidebar
          collapsed={collapsed}
          setCollapsed={setCollapsed}
          mobileOpen={mobileOpen}
          setMobileOpen={setMobileOpen}
        />

        <div className="flex-1 md:ml-0 ml-0">
          <div className={collapsed ? "md:pl-[76px]" : "md:pl-[260px]"}>
            <Header onOpenMobile={() => setMobileOpen(true)} />
            <main className="p-4">{children}</main>
          </div>
        </div>
      </div>
    </div>
  );
}
