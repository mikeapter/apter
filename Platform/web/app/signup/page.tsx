"use client";

import * as React from "react";
import Link from "next/link";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { Eye, EyeOff } from "lucide-react";
import { apiPost } from "@/lib/api";
import { setToken, setStoredUser } from "@/lib/auth";
import { track } from "@/lib/analytics";
import {
  validateName,
  validateEmail,
  validatePassword,
  validateConfirmPassword,
  passwordStrength,
  STRENGTH_LABELS,
} from "@/lib/validation";

const REFERRAL_OPTIONS = [
  "",
  "Search engine",
  "Social media",
  "Friend or colleague",
  "Blog or article",
  "Podcast",
  "Other",
] as const;

type RegisterResponse = {
  user_id: number;
  email: string;
  first_name: string;
  last_name: string;
  access_token: string;
  token_type: string;
};

type FieldErrors = {
  firstName?: string | null;
  lastName?: string | null;
  email?: string | null;
  password?: string | null;
  confirmPassword?: string | null;
};

export default function SignupPage() {
  const router = useRouter();

  const [firstName, setFirstName] = React.useState("");
  const [lastName, setLastName] = React.useState("");
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [confirmPassword, setConfirmPassword] = React.useState("");
  const [referralSource, setReferralSource] = React.useState("");
  const [showPassword, setShowPassword] = React.useState(false);
  const [showConfirm, setShowConfirm] = React.useState(false);

  const [touched, setTouched] = React.useState<Record<string, boolean>>({});
  const [serverError, setServerError] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);

  React.useEffect(() => {
    track("signup_started");
  }, []);

  const errors: FieldErrors = React.useMemo(
    () => ({
      firstName: validateName(firstName),
      lastName: validateName(lastName),
      email: validateEmail(email),
      password: validatePassword(password),
      confirmPassword: validateConfirmPassword(confirmPassword, password),
    }),
    [firstName, lastName, email, password, confirmPassword]
  );

  const strength = passwordStrength(password);
  const strengthInfo = STRENGTH_LABELS[strength];

  const isValid =
    !errors.firstName &&
    !errors.lastName &&
    !errors.email &&
    !errors.password &&
    !errors.confirmPassword;

  function handleBlur(field: string) {
    setTouched((prev) => ({ ...prev, [field]: true }));
  }

  function showError(field: keyof FieldErrors): string | null {
    if (!touched[field]) return null;
    return errors[field] ?? null;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    // Mark all fields as touched
    setTouched({
      firstName: true,
      lastName: true,
      email: true,
      password: true,
      confirmPassword: true,
    });

    if (!isValid) return;

    setSubmitting(true);
    setServerError("");

    const result = await apiPost<RegisterResponse>("/auth/register", {
      first_name: firstName.trim(),
      last_name: lastName.trim(),
      email: email.trim().toLowerCase(),
      password,
      referral_source: referralSource || undefined,
    });

    setSubmitting(false);

    if (!result.ok) {
      // Try to parse JSON detail from FastAPI error
      try {
        const parsed = JSON.parse(result.error);
        setServerError(parsed.detail || result.error);
      } catch {
        setServerError(result.error);
      }
      return;
    }

    // Store auth state (refresh token is set via HTTP-only cookie by the API)
    setToken(result.data.access_token);
    setStoredUser({
      id: result.data.user_id,
      email: result.data.email,
      first_name: result.data.first_name,
      last_name: result.data.last_name,
    });

    track("signup_completed", {
      user_id: result.data.user_id,
      referral_source: referralSource || undefined,
    });

    router.push("/dashboard");
  }

  return (
    <div className="min-h-screen flex flex-col justify-center py-12 px-4">
      <div className="auth-card">
        {/* Header */}
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
            Create your account
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Start with the free Observer tier. Upgrade anytime.
          </p>
        </div>

        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          {/* Name row */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label htmlFor="firstName" className="bt-label">
                First Name
              </label>
              <input
                id="firstName"
                type="text"
                autoComplete="given-name"
                className="bt-input h-10"
                value={firstName}
                onChange={(e) => setFirstName(e.target.value)}
                onBlur={() => handleBlur("firstName")}
                aria-invalid={!!showError("firstName")}
                aria-describedby={showError("firstName") ? "firstName-error" : undefined}
              />
              {showError("firstName") && (
                <p id="firstName-error" className="field-error">
                  {showError("firstName")}
                </p>
              )}
            </div>
            <div>
              <label htmlFor="lastName" className="bt-label">
                Last Name
              </label>
              <input
                id="lastName"
                type="text"
                autoComplete="family-name"
                className="bt-input h-10"
                value={lastName}
                onChange={(e) => setLastName(e.target.value)}
                onBlur={() => handleBlur("lastName")}
                aria-invalid={!!showError("lastName")}
                aria-describedby={showError("lastName") ? "lastName-error" : undefined}
              />
              {showError("lastName") && (
                <p id="lastName-error" className="field-error">
                  {showError("lastName")}
                </p>
              )}
            </div>
          </div>

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
              onBlur={() => handleBlur("email")}
              aria-invalid={!!showError("email")}
              aria-describedby={showError("email") ? "email-error" : undefined}
            />
            {showError("email") && (
              <p id="email-error" className="field-error">
                {showError("email")}
              </p>
            )}
          </div>

          {/* Password */}
          <div>
            <label htmlFor="password" className="bt-label">
              Password
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
                aria-invalid={!!showError("password")}
                aria-describedby="password-strength"
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
            {showError("password") && (
              <p className="field-error">{showError("password")}</p>
            )}
            {/* Strength meter */}
            {password.length > 0 && (
              <div id="password-strength" className="mt-2">
                <div className="flex gap-1 mb-1">
                  {[1, 2, 3, 4].map((level) => (
                    <div
                      key={level}
                      className={`h-1 flex-1 rounded-full transition-colors duration-200 ${
                        strength >= level ? strengthInfo.color : "bg-border"
                      }`}
                    />
                  ))}
                </div>
                <p className="text-xs text-muted-foreground">
                  {strengthInfo.label}
                </p>
              </div>
            )}
          </div>

          {/* Confirm password */}
          <div>
            <label htmlFor="confirmPassword" className="bt-label">
              Confirm Password
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
                aria-invalid={!!showError("confirmPassword")}
                aria-describedby={
                  showError("confirmPassword") ? "confirmPassword-error" : undefined
                }
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
            {showError("confirmPassword") && (
              <p id="confirmPassword-error" className="field-error">
                {showError("confirmPassword")}
              </p>
            )}
          </div>

          {/* Referral source (optional) */}
          <div>
            <label htmlFor="referralSource" className="bt-label">
              How did you hear about us?{" "}
              <span className="text-muted-foreground font-normal">(optional)</span>
            </label>
            <select
              id="referralSource"
              className="bt-input h-10 appearance-none"
              value={referralSource}
              onChange={(e) => setReferralSource(e.target.value)}
            >
              <option value="">Select...</option>
              {REFERRAL_OPTIONS.filter(Boolean).map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
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
            {submitting ? "Creating account..." : "Create Account"}
          </button>
        </form>

        {/* Footer */}
        <p className="mt-6 text-center text-sm text-muted-foreground">
          Already have an account?{" "}
          <Link
            href="/login"
            className="text-foreground underline underline-offset-4 hover:opacity-80 transition-opacity"
          >
            Sign in
          </Link>
        </p>

        {/* Legal compliance */}
        <p className="mt-4 text-center text-[11px] text-muted-foreground leading-relaxed">
          By creating an account you agree to our{" "}
          <Link href="/terms" className="underline underline-offset-2">
            Terms of Service
          </Link>{" "}
          and{" "}
          <Link href="/privacy" className="underline underline-offset-2">
            Privacy Policy
          </Link>
          . This platform provides analytical signals only and does not constitute
          investment advice.
        </p>
      </div>
    </div>
  );
}
