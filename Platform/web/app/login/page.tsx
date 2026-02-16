"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Eye, EyeOff } from "lucide-react";
import { apiPost, apiGet } from "@/lib/api";
import { setToken, setStoredUser } from "@/lib/auth";
import { track } from "@/lib/analytics";
import { validateEmail } from "@/lib/validation";

type LoginResponse =
  | { requires_2fa: true; user_id: number; message: string }
  | { access_token: string; token_type: string };

type ProfileResponse = {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
};

export default function LoginPage() {
  const router = useRouter();

  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [showPassword, setShowPassword] = React.useState(false);
  const [rememberDevice, setRememberDevice] = React.useState(false);

  const [emailTouched, setEmailTouched] = React.useState(false);
  const [serverError, setServerError] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);

  React.useEffect(() => {
    track("login_started");
  }, []);

  const emailError = emailTouched ? validateEmail(email) : null;
  const canSubmit = !validateEmail(email) && password.length > 0;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setEmailTouched(true);
    if (!canSubmit) return;

    setSubmitting(true);
    setServerError("");

    const result = await apiPost<LoginResponse>("/auth/login", {
      email: email.trim().toLowerCase(),
      password,
    });

    setSubmitting(false);

    if (!result.ok) {
      try {
        const parsed = JSON.parse(result.error);
        setServerError(parsed.detail || result.error);
      } catch {
        setServerError(result.error);
      }
      return;
    }

    // Handle 2FA
    if ("requires_2fa" in result.data && result.data.requires_2fa) {
      setServerError(
        "Two-factor authentication is enabled for this account. 2FA login UI is coming soon."
      );
      return;
    }

    const loginData = result.data as { access_token: string; token_type: string };
    setToken(loginData.access_token);

    // Fetch user profile to store name
    const profileResult = await apiGet<ProfileResponse>(
      "/api/me",
      undefined,
      loginData.access_token
    );

    if (profileResult.ok) {
      setStoredUser({
        id: profileResult.data.id,
        email: profileResult.data.email,
        first_name: profileResult.data.first_name,
        last_name: profileResult.data.last_name,
      });
    }

    track("login_completed");
    router.push("/dashboard");
  }

  return (
    <div className="min-h-screen flex flex-col justify-center py-12 px-4">
      <div className="auth-card">
        {/* Header */}
        <div className="mb-6">
          <Link
            href="/"
            className="flex items-center gap-2 mb-6 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-sm w-fit"
          >
            <div className="h-7 w-7 rounded-md bg-white/10 border border-white/10 flex items-center justify-center text-xs font-bold text-foreground">
              A
            </div>
            <span className="text-sm font-semibold text-foreground">
              Apter Financial
            </span>
          </Link>
          <h1 className="text-xl font-bold text-foreground">
            Sign in to your account
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Access your dashboard and signals.
          </p>
        </div>

        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          {/* Email */}
          <div>
            <label htmlFor="email" className="bt-label">
              Email
            </label>
            <input
              id="email"
              type="email"
              autoComplete="email"
              className="bt-input h-10"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onBlur={() => setEmailTouched(true)}
              aria-invalid={!!emailError}
              aria-describedby={emailError ? "email-error" : undefined}
            />
            {emailError && (
              <p id="email-error" className="field-error">
                {emailError}
              </p>
            )}
          </div>

          {/* Password */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label htmlFor="password" className="text-sm font-medium text-foreground">
                Password
              </label>
              <Link
                href="/forgot-password"
                className="text-xs text-muted-foreground hover:text-foreground transition-colors underline underline-offset-2"
              >
                Forgot password?
              </Link>
            </div>
            <div className="relative">
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                className="bt-input h-10 pr-10"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <button
                type="button"
                className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-muted-foreground hover:text-foreground transition-colors"
                onClick={() => setShowPassword((v) => !v)}
                tabIndex={-1}
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
          </div>

          {/* Remember device */}
          <div className="flex items-center gap-2">
            <input
              id="rememberDevice"
              type="checkbox"
              checked={rememberDevice}
              onChange={(e) => setRememberDevice(e.target.checked)}
              className="h-4 w-4 rounded border-border bg-background text-foreground accent-foreground"
            />
            <label
              htmlFor="rememberDevice"
              className="text-sm text-muted-foreground select-none"
            >
              Remember this device
            </label>
          </div>

          {/* Server error */}
          {serverError && (
            <div className="rounded-md border border-risk-off/40 bg-risk-off/10 px-3 py-2 text-sm text-risk-off">
              {serverError}
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={submitting}
            className="w-full h-11 rounded-md bg-foreground text-background text-sm font-medium transition-opacity duration-150 hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          >
            {submitting ? "Signing in..." : "Sign In"}
          </button>
        </form>

        {/* Footer */}
        <p className="mt-6 text-center text-sm text-muted-foreground">
          Don&apos;t have an account?{" "}
          <Link
            href="/signup"
            className="text-foreground underline underline-offset-4 hover:opacity-80 transition-opacity"
          >
            Create account
          </Link>
        </p>

        {/* Legal compliance */}
        <p className="mt-4 text-center text-[11px] text-muted-foreground leading-relaxed">
          This platform provides analytical signals only and does not constitute
          investment advice.
        </p>
      </div>
    </div>
  );
}
