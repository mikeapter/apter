import { useMemo, useState } from "react";
import Link from "next/link";

export default function Login2FA() {
  const [code, setCode] = useState("");
  const [backup, setBackup] = useState("");
  const [useBackup, setUseBackup] = useState(false);
  const [status, setStatus] = useState<"idle" | "verifying" | "ok" | "fail">("idle");
  const [message, setMessage] = useState<string>("");

  const canSubmit = useMemo(() => {
    if (useBackup) return backup.trim().length >= 6;
    return code.trim().length >= 6;
  }, [useBackup, code, backup]);

  async function verify() {
    setStatus("verifying");
    setMessage("");

    try {
      const payload = useBackup ? { backup_code: backup.trim() } : { code: code.trim() };

      // This endpoint is a stub unless your API implements it.
      // It exists ONLY to keep production builds valid and ready for wiring later.
      const res = await fetch("/api/2fa/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        setStatus("fail");
        setMessage("Verification could not be completed. Confirm API wiring and try again.");
        return;
      }

      setStatus("ok");
      setMessage("Verification accepted.");
    } catch {
      setStatus("fail");
      setMessage("Network error. Verification could not be completed.");
    }
  }

  return (
    <div className="min-h-screen bg-background text-foreground flex items-center justify-center px-4">
      <div className="w-full max-w-md border border-border bg-card rounded-md p-4">
        <div className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
          Security
        </div>
        <h1 className="mt-1 text-sm font-semibold tracking-tight">Two-Factor Verification</h1>

        <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
          Enter an authenticator code or a backup recovery code. No execution occurs here. This step is
          verification only.
        </p>

        <div className="mt-4 space-y-3">
          {!useBackup ? (
            <div>
              <div className="text-xs text-muted-foreground mb-1">Authenticator code</div>
              <input
                className="bt-input"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="6-digit code"
                inputMode="numeric"
              />
            </div>
          ) : (
            <div>
              <div className="text-xs text-muted-foreground mb-1">Backup code</div>
              <input
                className="bt-input"
                value={backup}
                onChange={(e) => setBackup(e.target.value)}
                placeholder="Recovery code"
              />
            </div>
          )}

          <div className="flex items-center justify-between">
            <button
              type="button"
              className="bt-button"
              onClick={() => setUseBackup((v) => !v)}
            >
              {useBackup ? "Use authenticator code" : "Use backup code"}
            </button>

            <button
              type="button"
              className="bt-button"
              disabled={!canSubmit || status === "verifying"}
              onClick={verify}
            >
              {status === "verifying" ? "Verifying…" : "Verify"}
            </button>
          </div>

          {status !== "idle" && (
            <div
              className={[
                "text-sm leading-relaxed",
                status === "ok" ? "text-risk-on" : status === "fail" ? "text-risk-off" : "text-muted-foreground",
              ].join(" ")}
            >
              {message}
            </div>
          )}

          <div className="pt-2 text-xs text-muted-foreground">
            Need to set up 2FA? Go to{" "}
            <Link className="underline" href="/settings/security">
              Security Settings
            </Link>
            .
          </div>
        </div>
      </div>
    </div>
  );
}
