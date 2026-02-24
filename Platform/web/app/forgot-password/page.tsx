"use client";

import * as React from "react";
import Link from "next/link";
import Image from "next/image";
import { apiPost } from "@/lib/api";
import { validateEmail } from "@/lib/validation";

export default function ForgotPasswordPage() {
  const [email, setEmail] = React.useState("");
  const [emailTouched, setEmailTouched] = React.useState(false);
  const [submitting, setSubmitting] = React.useState(false);
  const [submitted, setSubmitted] = React.useState(false);
  const [serverError, setServerError] = React.useState("");

  const emailError = emailTouched ? validateEmail(email) : null;
  const canSubmit = !validateEmail(email);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setEmailTouched(true);
    if (!canSubmit) return;

    setSubmitting(true);
    setServerError("");

    const result = await apiPost<{ detail: string }>("/auth/forgot-password", {
      email: email.trim().toLowerCase(),
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

    setSubmitted(true);
  }

  if (submitted) {
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
            Check your email
          </h1>
          <p className="text-sm text-muted-foreground mb-6">
            If an account with that email exists, we&apos;ve sent a password
            reset link. Please check your inbox and spam folder.
          </p>
          <Link
            href="/login"
            className="inline-flex h-10 items-center justify-center rounded-md border border-border bg-transparent px-4 text-sm font-medium text-foreground hover:bg-muted transition-colors"
          >
            Back to Sign In
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
            Reset your password
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Enter your email and we&apos;ll send you a reset link.
          </p>
        </div>

        <form onSubmit={handleSubmit} noValidate className="space-y-4">
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
            {submitting ? "Sending..." : "Send Reset Link"}
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
