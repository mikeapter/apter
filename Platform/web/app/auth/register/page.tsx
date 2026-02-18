"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

export default function RegisterPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState<string>("");

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setMessage("Creating account...");

    try {
      // Keep requests on /api/auth/* (proxied to backend)
      const res = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, email, password }),
      });

      if (!res.ok) {
        const txt = await res.text();
        setMessage(`Registration failed (${res.status})${txt ? `: ${txt}` : ""}`);
        return;
      }

      setMessage("Registration request accepted.");
    } catch {
      setMessage("Registration failed: network error.");
    }
  }

  return (
    <main className="min-h-screen bg-background text-foreground flex items-center justify-center p-6">
      <div className="w-full max-w-md border border-border rounded-xl bg-panel p-6">
        <h1 className="text-xl font-semibold tracking-tight">Create account</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Register to access platform features by tier.
        </p>

        <form onSubmit={onSubmit} className="mt-5 space-y-4">
          <div>
            <label className="block text-sm mb-1">Full name</label>
            <input
              className="w-full rounded-md border border-border bg-panel-2 px-3 py-2 outline-none"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoComplete="name"
              required
            />
          </div>

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
              autoComplete="new-password"
              required
            />
          </div>

          <button
            type="submit"
            className="w-full rounded-md border border-border px-3 py-2 font-semibold"
          >
            Create account
          </button>
        </form>

        <p className="mt-4 text-sm">
          Already have an account?{" "}
          <Link href="/auth/login" className="underline">
            Sign in
          </Link>
        </p>

        {message ? (
          <p className="mt-4 text-sm text-muted-foreground">{message}</p>
        ) : null}
      </div>
    </main>
  );
}
