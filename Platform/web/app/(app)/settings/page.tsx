"use client";

import { useState } from "react";
import Link from "next/link";
import { User, Shield, Bell, Palette, CreditCard, AlertTriangle } from "lucide-react";

function ToggleRow({ label, defaultOn = false }: { label: string; defaultOn?: boolean }) {
  const [on, setOn] = useState(defaultOn);
  return (
    <label className="flex items-center justify-between gap-3 py-2">
      <span className="text-sm">{label}</span>
      <button
        type="button"
        onClick={() => setOn(!on)}
        className={[
          "relative h-6 w-11 rounded-full border transition-colors",
          on ? "bg-risk-on/30 border-risk-on/50" : "bg-panel-2 border-border",
        ].join(" ")}
      >
        <span
          className={[
            "block h-4 w-4 rounded-full bg-foreground transition-transform",
            on ? "translate-x-5 ml-0.5" : "translate-x-0.5",
          ].join(" ")}
          style={{ marginTop: "3px" }}
        />
      </button>
    </label>
  );
}

export default function SettingsPage() {
  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Settings</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Account, security, notification, and display preferences.
        </p>
      </div>

      {/* Account */}
      <section className="bt-panel p-5 space-y-3">
        <div className="flex items-center gap-2">
          <User size={16} className="text-muted-foreground" />
          <div className="bt-panel-title">ACCOUNT</div>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label className="bt-label">Display Name</label>
            <input className="bt-input h-11" placeholder="Your name" defaultValue="" />
          </div>
          <div>
            <label className="bt-label">Phone</label>
            <input className="bt-input h-11" placeholder="+1 (555) 000-0000" />
          </div>
        </div>
        <p className="text-[10px] text-muted-foreground">
          Name and phone can also be updated on the Profile page.
        </p>
      </section>

      {/* Security */}
      <section className="bt-panel p-5 space-y-3">
        <div className="flex items-center gap-2">
          <Shield size={16} className="text-muted-foreground" />
          <div className="bt-panel-title">SECURITY</div>
        </div>
        <div className="space-y-3">
          <div>
            <label className="bt-label">Change Password</label>
            <div className="flex gap-2">
              <input className="bt-input h-11 flex-1" type="password" placeholder="Current password" />
              <input className="bt-input h-11 flex-1" type="password" placeholder="New password" />
            </div>
            <button type="button" className="bt-button h-9 mt-2 text-xs">
              Update Password
            </button>
          </div>
          <div className="border-t border-border pt-3">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-sm font-medium">Two-Factor Authentication</div>
                <div className="text-xs text-muted-foreground">Add an extra layer of security to your account.</div>
              </div>
              <span className="bt-chip border-border text-muted-foreground text-[10px]">Coming soon</span>
            </div>
          </div>
        </div>
      </section>

      {/* Notifications */}
      <section className="bt-panel p-5 space-y-3">
        <div className="flex items-center gap-2">
          <Bell size={16} className="text-muted-foreground" />
          <div className="bt-panel-title">NOTIFICATIONS</div>
        </div>
        <div className="divide-y divide-border">
          <ToggleRow label="Signal alerts" defaultOn={true} />
          <ToggleRow label="Watchlist price alerts" defaultOn={true} />
          <ToggleRow label="Product updates and announcements" defaultOn={false} />
        </div>
        <p className="text-[10px] text-muted-foreground">
          Notification preferences are saved locally. Email delivery is not active in the current release.
        </p>
      </section>

      {/* Preferences */}
      <section className="bt-panel p-5 space-y-3">
        <div className="flex items-center gap-2">
          <Palette size={16} className="text-muted-foreground" />
          <div className="bt-panel-title">PREFERENCES</div>
        </div>
        <div className="space-y-3">
          <div>
            <label className="bt-label">Theme</label>
            <select className="bt-input h-11" defaultValue="dark" disabled>
              <option value="dark">Dark (Institutional)</option>
            </select>
            <p className="text-[10px] text-muted-foreground mt-1">
              Apter Financial uses a fixed dark theme for consistency.
            </p>
          </div>
          <div>
            <label className="bt-label">Timezone</label>
            <select className="bt-input h-11" defaultValue="America/Chicago">
              <option value="America/New_York">Eastern (ET)</option>
              <option value="America/Chicago">Central (CT)</option>
              <option value="America/Denver">Mountain (MT)</option>
              <option value="America/Los_Angeles">Pacific (PT)</option>
              <option value="UTC">UTC</option>
            </select>
          </div>
        </div>
      </section>

      {/* Billing */}
      <section className="bt-panel p-5">
        <div className="flex items-center gap-2 mb-3">
          <CreditCard size={16} className="text-muted-foreground" />
          <div className="bt-panel-title">BILLING</div>
        </div>
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-sm">
              Current plan: <span className="font-semibold capitalize">Observer (Free)</span>
            </div>
            <div className="text-xs text-muted-foreground mt-1">
              Upgrade to Signals ($25/mo) or Pro ($49/mo) for advanced analytics.
            </div>
          </div>
          <Link className="bt-button h-10 px-4 shrink-0" href="/plans">
            View Plans
          </Link>
        </div>
      </section>

      {/* Danger Zone */}
      <section className="bt-panel p-5 border-risk-off/20">
        <div className="flex items-center gap-2 mb-3">
          <AlertTriangle size={16} className="text-risk-off" />
          <div className="bt-panel-title text-risk-off">DANGER ZONE</div>
        </div>
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-sm font-medium">Delete Account</div>
            <div className="text-xs text-muted-foreground mt-1">
              Permanently delete your account and all associated data. This action cannot be undone.
            </div>
          </div>
          <button
            type="button"
            className="bt-button h-10 px-4 shrink-0 border-risk-off/40 text-risk-off hover:bg-risk-off/10"
            disabled
          >
            Delete Account
          </button>
        </div>
      </section>
    </div>
  );
}
