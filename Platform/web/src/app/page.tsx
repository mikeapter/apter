"use client";

import { useEffect, useState } from "react";

type BotStatus = {
  bot_id: string;
  running: boolean;
  pid?: number | null;
  script?: string | null;
};

export default function Home() {
  const API = process.env.NEXT_PUBLIC_API_BASE!;
  const KEY = process.env.NEXT_PUBLIC_API_KEY!;
  const BOT_ID = "opening";

  const [status, setStatus] = useState<BotStatus | null>(null);
  const [logs, setLogs] = useState<string>("");

  async function apiGet(path: string) {
    const res = await fetch(`${API}${path}`, {
      headers: { "X-API-Key": KEY },
      cache: "no-store",
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  async function apiPost(path: string, body?: any) {
    const res = await fetch(`${API}${path}`, {
      method: "POST",
      headers: {
        "X-API-Key": KEY,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body ?? {}),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  async function refresh() {
    const s = await apiGet(`/bots/${BOT_ID}/status`);
    setStatus(s);
    const l = await apiGet(`/bots/${BOT_ID}/logs`);
    setLogs(l.tail || "");
  }

  async function startBot() {
    await apiPost(`/bots/${BOT_ID}/start`, {
      script_rel: "scripts/run_opening.py",
      args: [],
    });
    await refresh();
  }

  async function stopBot() {
    await apiPost(`/bots/${BOT_ID}/stop`);
    await refresh();
  }

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 3000);
    return () => clearInterval(t);
  }, []);

  return (
    <main style={{ padding: 24, fontFamily: "system-ui" }}>
      <h1 style={{ fontSize: 28, fontWeight: 700 }}>
        BotTrader Platform (Local)
      </h1>
      <p style={{ opacity: 0.7 }}>Control Plane + Logs (starter)</p>

      <section style={{ marginTop: 20, padding: 16, border: "1px solid #333", borderRadius: 10 }}>
        <h2>Bot: {BOT_ID}</h2>
        <div><b>Running:</b> {status?.running ? "YES" : "NO"}</div>
        <div><b>PID:</b> {status?.pid ?? "-"}</div>
        <div><b>Script:</b> {status?.script ?? "-"}</div>

        <div style={{ display: "flex", gap: 10, marginTop: 12 }}>
          <button onClick={startBot}>Start</button>
          <button onClick={stopBot}>Stop</button>
          <button onClick={refresh}>Refresh</button>
        </div>
      </section>

      <section style={{ marginTop: 20, padding: 16, border: "1px solid #333", borderRadius: 10 }}>
        <h2>Logs (tail)</h2>
        <pre style={{ marginTop: 10, padding: 12, background: "#111", color: "#0f0" }}>
          {logs || "(no logs yet)"}
        </pre>
      </section>
    </main>
  );
}
