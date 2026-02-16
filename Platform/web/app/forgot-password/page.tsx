import Link from "next/link";

export default function ForgotPasswordPage() {
  return (
    <div className="min-h-screen flex flex-col justify-center py-12 px-4">
      <div className="auth-card text-center">
        <Link
          href="/"
          className="flex items-center gap-2 mb-6 justify-center focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded-sm w-fit mx-auto"
        >
          <div className="h-7 w-7 rounded-md bg-white/10 border border-white/10 flex items-center justify-center text-xs font-bold text-foreground">
            A
          </div>
          <span className="text-sm font-semibold text-foreground">
            Apter Financial
          </span>
        </Link>
        <h1 className="text-xl font-bold text-foreground mb-2">
          Reset your password
        </h1>
        <p className="text-sm text-muted-foreground mb-6">
          Password reset functionality is coming soon. Please contact{" "}
          <a
            href="mailto:support@apterfinancial.com"
            className="text-foreground underline underline-offset-2"
          >
            support@apterfinancial.com
          </a>{" "}
          for assistance.
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
