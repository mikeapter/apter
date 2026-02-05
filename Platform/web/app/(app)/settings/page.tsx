"use client";

import Link from "next/link";

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <div className="text-2xl font-semibold">Settings</div>
        <div className="text-muted-foreground">Account, security, and subscription settings.</div>
      </div>

      <div className="rounded-lg border border-border bg-card p-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="font-semibold">Subscription</div>
            <div className="text-sm text-muted-foreground">
              Manage plan tier and view included features.
            </div>
          </div>
          <Link
            className="h-10 px-3 rounded-md border border-border hover:bg-muted text-sm font-semibold flex items-center"
            href="/plans"
          >
            View Plans
          </Link>
        </div>
      </div>
    </div>
  );
}
