"use client";

import Link from "next/link";
import { User, CreditCard, Bell } from "lucide-react";

export default function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <div className="text-2xl font-semibold">Settings</div>
        <div className="text-muted-foreground text-sm">Account, subscription, and notification preferences.</div>
      </div>

      {/* Account */}
      <section className="bt-panel p-4 space-y-3">
        <div className="flex items-center gap-2">
          <User size={16} className="text-muted-foreground" />
          <div className="bt-panel-title">ACCOUNT</div>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground block mb-1">Display Name</label>
            <input className="bt-input" placeholder="Your name" defaultValue="Demo User" />
          </div>
          <div>
            <label className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground block mb-1">Email</label>
            <input className="bt-input" placeholder="Email address" defaultValue="user@example.com" readOnly />
          </div>
        </div>
      </section>

      {/* Subscription */}
      <section className="bt-panel p-4">
        <div className="flex items-center gap-2 mb-3">
          <CreditCard size={16} className="text-muted-foreground" />
          <div className="bt-panel-title">SUBSCRIPTION</div>
        </div>
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-sm">
              Current plan: <span className="font-semibold">Free</span>
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              Upgrade to Standard ($25/mo) or Pro ($49/mo) for advanced analytics, risk engine, and AI features.
            </div>
          </div>
          <Link className="bt-button h-10 px-4" href="/plans">
            View Plans
          </Link>
        </div>
      </section>

      {/* Notifications */}
      <section className="bt-panel p-4 space-y-3">
        <div className="flex items-center gap-2">
          <Bell size={16} className="text-muted-foreground" />
          <div className="bt-panel-title">NOTIFICATIONS</div>
        </div>
        <div className="space-y-2">
          <label className="flex items-center gap-3 text-sm">
            <input type="checkbox" defaultChecked className="accent-[hsl(var(--risk-on))]" />
            Email alerts for earnings reports on watchlist tickers
          </label>
          <label className="flex items-center gap-3 text-sm">
            <input type="checkbox" defaultChecked className="accent-[hsl(var(--risk-on))]" />
            Weekly portfolio performance summary
          </label>
          <label className="flex items-center gap-3 text-sm">
            <input type="checkbox" className="accent-[hsl(var(--risk-on))]" />
            Grade change notifications
          </label>
        </div>
        <div className="text-xs text-muted-foreground">
          Notification preferences are saved locally. Email delivery is not active in the current release.
        </div>
      </section>
    </div>
  );
}
