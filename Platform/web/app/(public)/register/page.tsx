"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { apiPost } from "@/lib/api";
import { setToken } from "@/lib/auth";

type RegisterResponse = {
  user_id: number;
  email: string;
  access_token: string;
  token_type: string;
};

export default function RegisterPage() {
  const router = useRouter();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleRegister(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (password !== confirm) {
      setError("Passwords do not match.");
      return;
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setLoading(true);
    const r = await apiPost<RegisterResponse>("/auth/register", {
      email,
      password,
    });
    setLoading(false);

    if (!r.ok) {
      setError(r.error);
      return;
    }

    setToken(r.data.access_token);
    router.push("/dashboard");
  }

  return (
    <div className="flex items-center justify-center min-h-[60vh] px-4">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-semibold mb-2">Create Account</h1>
        <p className="text-sm text-muted-foreground mb-6">
          Start with the free Observer tier. Upgrade anytime.
        </p>

        <form onSubmit={handleRegister} className="space-y-4">
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
          <input
            className="bt-input h-11"
            type="password"
            placeholder="Confirm password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            required
          />
          {error && <div className="text-sm text-red-400">{error}</div>}
          <button
            type="submit"
            disabled={loading}
            className="bt-button w-full h-11 justify-center border-risk-on/40 text-risk-on hover:bg-risk-on/10"
          >
            {loading ? "Creating account..." : "Register"}
          </button>
        </form>

        <p className="mt-6 text-sm text-muted-foreground text-center">
          Already have an account?{" "}
          <Link href="/login" className="text-foreground hover:underline">
            Login
          </Link>
        </p>
      </div>
    </div>
  );
}
