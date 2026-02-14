"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { apiPost } from "@/lib/api";
import { setToken } from "@/lib/auth";

type LoginResponse =
  | { requires_2fa: true; user_id: number; message: string }
  | { access_token: string; token_type: string };

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams?.get("next") || "/dashboard";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // 2FA state
  const [twoFaUserId, setTwoFaUserId] = useState<number | null>(null);
  const [twoFaCode, setTwoFaCode] = useState("");

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    const r = await apiPost<LoginResponse>("/auth/login", { email, password });
    setLoading(false);

    if (!r.ok) {
      setError(r.error);
      return;
    }

    if ("requires_2fa" in r.data && r.data.requires_2fa) {
      setTwoFaUserId(r.data.user_id);
      return;
    }

    if ("access_token" in r.data) {
      setToken(r.data.access_token);
      router.push(next);
    }
  }

  async function handle2FA(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    const r = await apiPost<{ access_token: string; token_type: string }>(
      "/auth/login/2fa",
      { user_id: twoFaUserId, code: twoFaCode, trust_device: false }
    );
    setLoading(false);

    if (!r.ok) {
      setError(r.error);
      return;
    }

    setToken(r.data.access_token);
    router.push(next);
  }

  if (twoFaUserId !== null) {
    return (
      <div className="flex items-center justify-center min-h-[60vh] px-4">
        <div className="w-full max-w-sm">
          <h1 className="text-2xl font-semibold mb-2">Two-Factor Authentication</h1>
          <p className="text-sm text-muted-foreground mb-6">
            Enter the code from your authenticator app.
          </p>

          <form onSubmit={handle2FA} className="space-y-4">
            <input
              className="bt-input h-11"
              placeholder="6-digit code"
              value={twoFaCode}
              onChange={(e) => setTwoFaCode(e.target.value)}
              autoFocus
            />
            {error && <div className="text-sm text-red-400">{error}</div>}
            <button
              type="submit"
              disabled={loading}
              className="bt-button w-full h-11 justify-center border-risk-on/40 text-risk-on hover:bg-risk-on/10"
            >
              {loading ? "Verifying..." : "Verify"}
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center min-h-[60vh] px-4">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-semibold mb-2">Login</h1>
        <p className="text-sm text-muted-foreground mb-6">
          Sign in to access your dashboard.
        </p>

        <form onSubmit={handleLogin} className="space-y-4">
          <input
            className="bt-input h-11"
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoFocus
          />
          <input
            className="bt-input h-11"
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          {error && <div className="text-sm text-red-400">{error}</div>}
          <button
            type="submit"
            disabled={loading}
            className="bt-button w-full h-11 justify-center border-risk-on/40 text-risk-on hover:bg-risk-on/10"
          >
            {loading ? "Signing in..." : "Login"}
          </button>
        </form>

        <p className="mt-6 text-sm text-muted-foreground text-center">
          Don&apos;t have an account?{" "}
          <Link href="/register" className="text-foreground hover:underline">
            Register
          </Link>
        </p>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="flex items-center justify-center min-h-[60vh]"><div className="text-sm text-muted-foreground">Loading...</div></div>}>
      <LoginForm />
    </Suspense>
  );
}
