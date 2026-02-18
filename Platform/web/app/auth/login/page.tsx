"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState<string>("");

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setMessage("Signing in...");

    try {
      // Keep requests on /api/auth/* (proxied to backend)
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        const txt = await res.text();
        setMessage(`Login failed (${res.status})${txt ? `: ${txt}` : ""}`);
        return;
      }

      setMessage("Login request accepted.");
    } catch (err) {
      setMessage("Login failed: network error.");
    }
  }

  return (
    <main className="min-h-screen bg-background text-foreground flex items-center justify-center p-6">
      <div className="w-full max-w-md border border-border rounded-xl bg-panel p-6">
        <h1 className="text-xl font-semibold tracking-tight">Sign in</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Access your Apter Financial control panel.
        </p>

        <form onSubmit={onSubmit} className="mt-5 space-y-4">
          <div>
            <label className="block text-sm mb-1">Email</label>
            <input
              className="w-full rounded-md border border-border bg-panel-2 px-3 py-2 outline-none"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
            />
          </div>

          <div>
            <label className="block text-sm mb-1">Password</label>
            <input
              className="w-full rounded-md border border-border bg-panel-2 px-3 py-2 outline-none"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </div>

          <button
            type="submit"
            className="w-full rounded-md border border-border px-3 py-2 font-semibold"
          >
            Sign in
          </button>
        </form>

        <p className="mt-4 text-sm">
          New here?{" "}
          <Link href="/auth/register" className="underline">
            Create account
          </Link>
        </p>

        {message ? (
          <p className="mt-4 text-sm text-muted-foreground">{message}</p>
        ) : null}
      </div>
    </main>
  );
}
