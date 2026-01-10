"use client";

import { useEffect, useMemo, useState } from "react";
import { apiGet, apiPost } from "@/lib/api";

type Profile = { id: string; name: string };

type Run = {
  run_id: string;
  profile_id: string;
  status: string;
  started_at: number;
  stopped_at?: number | null;
};

export default function Home() {
  const [health, setHealth] = useState<any>(null);
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [selectedProfile, setSelectedProfile] = useState<string>("paper");
  const [selectedRun, setSelectedRun] = useState<string>("");
  const [logs, setLogs] = useState<string[]>([]);
  const [err, setErr] = useState<string>("");

  const activeRunId = useMemo(
    () => runs.find((r) => r.status === "running")?.run_id || "",
    [runs]
  );

  async function refresh() {
    setErr("");
    try {
      const [h, p, r] = await Promise.all([
        apiGet("/health"),
        apiGet("/v1/profiles"),
        apiGet("/v1/runs")
      ]);
      setHealth(h);
      setProfiles(p);
      setRuns(r);

      // keep selections sane
      if (!p.find((x: any) => x.id === selectedProfile) && p.length) {
        setSelectedProfile(p[0].id);
      }
      if (!selectedRun && r.length) setSelectedRun(r[0].run_id);
    } catch (e: any) {
      setErr(e?.message || String(e));
    }
  }

  async function loadLogs(runId: string) {
    if (!runId) return;
    setErr("");
    try {
      const out = await apiGet(`/v1/runs/${runId}/logs`);
      setLogs(out.lines || []);
    } catch (e: any) {
      setErr(e?.message || String(e));
    }
  }

  async function start() {
    setErr("");
    try {
      await apiPost("/v1/bot/start", { profile_id: selectedProfile });
      await refresh();
    } catch (e: any) {
      setErr(e?.message || String(e));
    }
  }

  async function stop() {
    setErr("");
    try {
      // backend supports optional run_id; we pass the active one if present
      await apiPost("/v1/bot/stop", { run_id: activeRunId || null });
      await refresh();
      if (activeRunId) await loadLogs(activeRunId);
    } catch (e: any) {
      setErr(e?.message || String(e));
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  return (
    <main style={{ padding: 16, maxWidth: 980, margin: "0 auto" }}>
      <h1 style={{ fontSize: 28, fontWeight: 800 }}>BotTrader Control Plane</h1>

      <div style={{ marginTop: 10, opacity: 0.85 }}>
        API Base: <code>{process.env.NEXT_PUBLIC_API_BASE || "http://127.0.0.1:8000"}</code>
      </div>

      {err ? (
        <div style={{ marginTop: 12, padding: 12, border: "1px solid #ff6b6b", borderRadius: 8 }}>
          <b>Error:</b> {err}
        </div>
      ) : null}

      <section style={{ marginTop: 18, padding: 12, border: "1px solid #333", borderRadius: 8 }}>
        <h2 style={{ fontSize: 18, fontWeight: 700 }}>Health</h2>
        <pre style={{ marginTop: 10, padding: 12, border: "1px solid #555", borderRadius: 8 }}>
          {health ? JSON.stringify(health, null, 2) : "(not loaded yet)"}
        </pre>

        <button onClick={refresh} style={{ marginTop: 10, padding: "8px 12px" }}>
          Refresh
        </button>
      </section>

      <section style={{ marginTop: 18, padding: 12, border: "1px solid #333", borderRadius: 8 }}>
        <h2 style={{ fontSize: 18, fontWeight: 700 }}>Start / Stop</h2>

        <div style={{ display: "flex", gap: 12, alignItems: "center", marginTop: 10, flexWrap: "wrap" }}>
          <label>
            Profile:&nbsp;
            <select
              value={selectedProfile}
              onChange={(e) => setSelectedProfile(e.target.value)}
              style={{ padding: "6px 10px" }}
            >
              {profiles.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.id} — {p.name}
                </option>
              ))}
            </select>
          </label>

          <button onClick={start} style={{ padding: "8px 12px" }}>Start Bot</button>
          <button onClick={stop} style={{ padding: "8px 12px" }}>Stop Bot</button>

          <span style={{ opacity: 0.85 }}>
            Active run: <b>{activeRunId || "none"}</b>
          </span>
        </div>
      </section>

      <section style={{ marginTop: 18, padding: 12, border: "1px solid #333", borderRadius: 8 }}>
        <h2 style={{ fontSize: 18, fontWeight: 700 }}>Runs</h2>

        <div style={{ marginTop: 10, display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <select
            value={selectedRun}
            onChange={(e) => setSelectedRun(e.target.value)}
            style={{ padding: "6px 10px", minWidth: 360 }}
          >
            <option value="">(select a run)</option>
            {runs.map((r) => (
              <option key={r.run_id} value={r.run_id}>
                {r.run_id} — {r.profile_id} — {r.status}
              </option>
            ))}
          </select>

          <button
            onClick={() => loadLogs(selectedRun)}
            style={{ padding: "8px 12px" }}
            disabled={!selectedRun}
          >
            Load Logs
          </button>
        </div>

        <pre style={{ marginTop: 12, padding: 12, border: "1px solid #555", borderRadius: 8, minHeight: 180 }}>
          {logs.length ? logs.join("\n") : "(no logs yet)"}
        </pre>
      </section>
    </main>
  );
}
