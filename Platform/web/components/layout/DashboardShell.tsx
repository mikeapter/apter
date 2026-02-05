"use client";

import * as React from "react";
import AppShell from "./AppShell";

export type DashboardShellProps = {
  children: React.ReactNode;
};

export function DashboardShell({ children }: DashboardShellProps) {
  return <AppShell>{children}</AppShell>;
}

export default DashboardShell;
