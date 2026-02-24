"use client";

import * as React from "react";
import Link from "next/link";
import Image from "next/image";
import { useSearchParams } from "next/navigation";
import { Eye, EyeOff } from "lucide-react";
import { apiPost } from "@/lib/api";
import { validatePassword, validateConfirmPassword } from "@/lib/validation";

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const token = searchParams?.get("token") || "";

  const [password, setPassword] = React.useState("");
  const [confirmPassword, setConfirmPassword] = React.useState("");
  const [showPassword, setShowPassword] = React.useState(false);
  const [showConfirm, setShowConfirm] = React.useState(false);
  const [touched, setTouched] = React.useState<Record<string, boolean>>({});
  const [submitting, setSubmitting] = React.useState(false);
  const [serverError, setServerError] = React.useState("");
  const [success, setSuccess] = React.useState(false);

  const passwordError = touched.password ? validatePassword(password) : null;
  const confirmError = touched.confirmPassword
    ? validateConfirmPassword(confirmPassword, password)
    : null;

  const isValid = !validatePassword(password) && !validateConfirmPassword(confirmPassword, password);

  function handleBlur(field: string) {
    setTouched((prev) => ({ ...prev, [field]: true }));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setTouched({ password: true, confirmPassword: true });
    if (!isValid || !token) return;

    setSubmitting(true);
    setServerError("");

    const result = await apiPost<{ detail: string }>("/auth/reset-password", {
      token,
      new_password: password,
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

    setSuccess(true);
  }

  if (!token) {
    return (
      <div className="min-h-screen flex flex-col justify-center py-12 px-4">
        <div className="auth-card text-center">
          <h1 className="text-xl font-bold text-foreground mb-2">
            Invalid reset link
          </h1>
          <p className="text-sm text-muted-foreground mb-6">
            This password reset link is invalid or has expired. Please request
            a new one.
          </p>
          <Link
            href="/forgot-password"
            className="inline-flex h-10 items-center justify-center rounded-md bg-foreground text-background px-4 text-sm font-medium hover:opacity-90 transition-opacity"
          >
            Request New Link
          </Link>
        </div>
      </div>
    );
  }

  if (success) {
    return (
      <div className="min-h-screen flex flex-col justify-center py-12 px-4">
        <div className="auth-card text-center">
          <Link
            href="/"
            className="flex items-center gap-2.5 mb-6 justify-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-sm w-fit mx-auto"
          >
            <Image
              src="/logo.png"
              alt="Apter Financial"
              width={32}
              height={32}
              priority
              className="h-8 w-8 rounded-full"
            />
            <span className="text-sm font-semibold text-foreground">
              Apter Financial
            </span>
          </Link>
          <h1 className="text-xl font-bold text-foreground mb-2">
            Password reset
          </h1>
          <p className="text-sm text-muted-foreground mb-6">
            Your password has been reset successfully. You can now sign in with
            your new password.
          </p>
          <Link
            href="/login"
            className="inline-flex h-10 items-center justify-center rounded-md bg-foreground text-background px-4 text-sm font-medium hover:opacity-90 transition-opacity"
          >
            Sign In
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col justify-center py-12 px-4">
      <div className="auth-card">
        <div className="mb-6">
          <Link
            href="/"
            className="flex items-center gap-2.5 mb-6 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-sm w-fit"
          >
            <Image
              src="/logo.png"
              alt="Apter Financial"
              width={32}
              height={32}
              priority
              className="h-8 w-8 rounded-full"
            />
            <span className="text-sm font-semibold text-foreground">
              Apter Financial
            </span>
          </Link>
          <h1 className="text-xl font-bold text-foreground">
            Set a new password
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Enter your new password below.
          </p>
        </div>

        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          {/* Password */}
          <div>
            <label htmlFor="password" className="bt-label">
              New Password
            </label>
            <div className="relative">
              <input
                id="password"
                type={showPassword ? "text" : "password"}
                autoComplete="new-password"
                className="bt-input h-10 pr-10"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                onBlur={() => handleBlur("password")}
                aria-invalid={!!passwordError}
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
            {passwordError && (
              <p className="field-error">{passwordError}</p>
            )}
          </div>

          {/* Confirm Password */}
          <div>
            <label htmlFor="confirmPassword" className="bt-label">
              Confirm New Password
            </label>
            <div className="relative">
              <input
                id="confirmPassword"
                type={showConfirm ? "text" : "password"}
                autoComplete="new-password"
                className="bt-input h-10 pr-10"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                onBlur={() => handleBlur("confirmPassword")}
                aria-invalid={!!confirmError}
              />
              <button
                type="button"
                className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-muted-foreground hover:text-foreground transition-colors"
                onClick={() => setShowConfirm((v) => !v)}
                tabIndex={-1}
                aria-label={showConfirm ? "Hide password" : "Show password"}
              >
                {showConfirm ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
            {confirmError && (
              <p className="field-error">{confirmError}</p>
            )}
          </div>

          {serverError && (
            <div className="rounded-md border border-risk-off/40 bg-risk-off/10 px-3 py-2 text-sm text-risk-off">
              {serverError}
            </div>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full h-11 rounded-md bg-foreground text-background text-sm font-medium transition-opacity duration-150 hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          >
            {submitting ? "Resetting..." : "Reset Password"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-muted-foreground">
          Remember your password?{" "}
          <Link
            href="/login"
            className="text-foreground underline underline-offset-4 hover:opacity-80 transition-opacity"
          >
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <React.Suspense fallback={
      <div className="min-h-screen flex flex-col justify-center py-12 px-4">
        <div className="auth-card text-center">
          <p className="text-sm text-muted-foreground">Loading...</p>
        </div>
      </div>
    }>
      <ResetPasswordForm />
    </React.Suspense>
  );
}
