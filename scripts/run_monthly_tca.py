from __future__ import annotations
from _bootstrap import bootstrap
bootstrap()


import argparse
import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


def _try_parse_ts(ts: Any) -> Optional[datetime]:
    """
    Accepts:
      - epoch seconds float/int (your trades.jsonl uses this)
      - ISO string (2025-12-30T...)
    Returns UTC datetime.
    """
    if ts is None:
        return None

    # epoch seconds
    if isinstance(ts, (int, float)):
        try:
            return datetime.fromtimestamp(float(ts), tz=timezone.utc)
        except Exception:
            return None

    # string
    try:
        s = str(ts).strip()
        if not s:
            return None
        # If it's a numeric string, treat as epoch seconds
        if s.replace(".", "", 1).isdigit():
            return datetime.fromtimestamp(float(s), tz=timezone.utc)

        # ISO-ish
        # Support trailing Z
        s = s.replace("Z", "+00:00")
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _month_key(dt: datetime) -> str:
    return f"{dt.year:04d}-{dt.month:02d}"


def _find_trades_log(repo_root: Path) -> Optional[Path]:
    candidates = [
        repo_root / "Data" / "Logs" / "trades.jsonl",
        repo_root / "Data" / "logs" / "trades.jsonl",
        repo_root / "data" / "logs" / "trades.jsonl",
        repo_root / "data" / "Logs" / "trades.jsonl",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def _safe_float(x: Any) -> Optional[float]:
    try:
        if x is None:
            return None
        v = float(x)
        if math.isnan(v) or math.isinf(v):
            return None
        return v
    except Exception:
        return None


def _mid(bid: Optional[float], ask: Optional[float]) -> Optional[float]:
    if bid is None or ask is None:
        return None
    if bid <= 0 or ask <= 0:
        return None
    return (bid + ask) / 2.0


def _bps_cost(side: str, arrival: Optional[float], fill: Optional[float]) -> Optional[float]:
    if arrival is None or fill is None or arrival <= 0:
        return None
    s = (side or "").upper()
    if s == "BUY":
        return (fill - arrival) / arrival * 10000.0
    if s == "SELL":
        return (arrival - fill) / arrival * 10000.0
    return None


@dataclass
class Row:
    ts: datetime
    month: str
    event_type: str
    status: str
    symbol: str
    side: str
    qty: int
    strategy: str
    broker: str
    venue: Optional[str]
    reason: Optional[str]
    arrival_price: Optional[float]
    fill_price: Optional[float]
    latency_ms: Optional[float]


def _read_rows(path: Path) -> List[Row]:
    rows: List[Row] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue

            ts = _try_parse_ts(obj.get("ts"))
            if ts is None:
                continue

            rows.append(
                Row(
                    ts=ts,
                    month=_month_key(ts),
                    event_type=str(obj.get("event_type") or ""),
                    status=str(obj.get("status") or ""),
                    symbol=str(obj.get("symbol") or ""),
                    side=str(obj.get("side") or ""),
                    qty=int(obj.get("qty") or 0),
                    strategy=str(obj.get("strategy") or ""),
                    broker=str(obj.get("broker") or ""),
                    venue=obj.get("venue"),
                    reason=obj.get("reason"),
                    arrival_price=_safe_float(obj.get("arrival_price")),
                    fill_price=_safe_float(obj.get("fill_price")),
                    latency_ms=_safe_float(obj.get("latency_ms")),
                )
            )
    return rows


def _percentiles(vals: List[float], ps: List[int]) -> Dict[int, float]:
    if not vals:
        return {}
    vals = sorted(vals)
    out: Dict[int, float] = {}
    n = len(vals)
    for p in ps:
        if n == 1:
            out[p] = vals[0]
            continue
        k = (p / 100) * (n - 1)
        lo = int(math.floor(k))
        hi = int(math.ceil(k))
        if lo == hi:
            out[p] = vals[lo]
        else:
            w = k - lo
            out[p] = vals[lo] * (1 - w) + vals[hi] * w
    return out


def _write_report(
    *,
    repo_root: Path,
    month: str,
    out_path: Path,
    rows: List[Row],
) -> None:
    total = len(rows)

    blocked = [r for r in rows if r.status.upper() == "BLOCKED" or r.event_type.upper() == "ORDER_BLOCKED"]
    fills = [
        r
        for r in rows
        if (r.status.upper() in ("FILLED", "PAPER", "SIM_FILLED"))
        or (r.fill_price is not None and r.qty and r.qty != 0 and r.side.upper() in ("BUY", "SELL"))
    ]

    # blocked breakdown
    reason_counts = Counter([(r.reason or "UNKNOWN") for r in blocked])

    # fill metrics
    costs: List[float] = []
    latencies: List[float] = []
    for r in fills:
        c = _bps_cost(r.side, r.arrival_price, r.fill_price)
        if c is not None:
            costs.append(c)
        if r.latency_ms is not None:
            latencies.append(r.latency_ms)

    cost_p = _percentiles(costs, [50, 75, 90, 95])
    lat_p = _percentiles(latencies, [50, 75, 90, 95])

    def esc(s: Any) -> str:
        return (
            str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    html = []
    html.append("<html><head><meta charset='utf-8'>")
    html.append("<title>TCA Report</title>")
    html.append(
        "<style>"
        "body{font-family:Arial, sans-serif; margin:20px;}"
        "h1,h2{margin:0.2em 0;}"
        "table{border-collapse:collapse; width:100%; margin:10px 0;}"
        "th,td{border:1px solid #ddd; padding:8px; font-size:14px;}"
        "th{background:#f5f5f5; text-align:left;}"
        ".kpi{display:flex; gap:16px; flex-wrap:wrap; margin:12px 0;}"
        ".card{border:1px solid #ddd; border-radius:8px; padding:10px 12px; min-width:220px;}"
        ".muted{color:#666;}"
        "</style>"
    )
    html.append("</head><body>")

    html.append(f"<h1>TCA + Monitoring Report</h1>")
    html.append(f"<div class='muted'>Month: <b>{esc(month)}</b> | Generated: {esc(datetime.now(timezone.utc).isoformat())}</div>")

    html.append("<div class='kpi'>")
    html.append(f"<div class='card'><div class='muted'>Total events</div><div style='font-size:26px'><b>{total}</b></div></div>")
    html.append(f"<div class='card'><div class='muted'>Fills</div><div style='font-size:26px'><b>{len(fills)}</b></div></div>")
    html.append(f"<div class='card'><div class='muted'>Blocked</div><div style='font-size:26px'><b>{len(blocked)}</b></div></div>")
    html.append("</div>")

    # If no rows at all, still write a helpful report
    if total == 0:
        html.append("<h2>No events found</h2>")
        html.append("<p class='muted'>No trades or blocks were logged for this month.</p>")
        html.append("</body></html>")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("\n".join(html), encoding="utf-8")
        return

    # Blocked section
    html.append("<h2>Blocked decisions</h2>")
    if not blocked:
        html.append("<p class='muted'>No blocked decisions recorded.</p>")
    else:
        html.append("<table><tr><th>Reason</th><th>Count</th></tr>")
        for reason, cnt in reason_counts.most_common():
            html.append(f"<tr><td>{esc(reason)}</td><td>{cnt}</td></tr>")
        html.append("</table>")

    # Fill cost section
    html.append("<h2>Transaction Cost (fills only)</h2>")
    if not fills:
        html.append("<p class='muted'>No fills recorded. (You may only have BLOCKED events.)</p>")
    else:
        avg_cost = sum(costs) / len(costs) if costs else None
        html.append("<div class='kpi'>")
        html.append(
            f"<div class='card'><div class='muted'>Avg cost (bps)</div><div style='font-size:22px'><b>{esc(round(avg_cost, 2) if avg_cost is not None else 'n/a')}</b></div></div>"
        )
        html.append(
            f"<div class='card'><div class='muted'>P50/P90 cost (bps)</div><div style='font-size:22px'><b>{esc(round(cost_p.get(50, 0.0), 2) if cost_p else 'n/a')} / {esc(round(cost_p.get(90, 0.0), 2) if cost_p else 'n/a')}</b></div></div>"
        )
        html.append("</div>")

        html.append("<table><tr><th>Metric</th><th>Value</th></tr>")
        for p in [50, 75, 90, 95]:
            if p in cost_p:
                html.append(f"<tr><td>Cost P{p} (bps)</td><td>{esc(round(cost_p[p], 3))}</td></tr>")
        for p in [50, 75, 90, 95]:
            if p in lat_p:
                html.append(f"<tr><td>Latency P{p} (ms)</td><td>{esc(round(lat_p[p], 2))}</td></tr>")
        html.append("</table>")

    # Recent events sample
    html.append("<h2>Recent events (sample)</h2>")
    html.append("<table><tr><th>TS (UTC)</th><th>Type</th><th>Status</th><th>Symbol</th><th>Side</th><th>Qty</th><th>Reason</th></tr>")
    for r in sorted(rows, key=lambda x: x.ts, reverse=True)[:50]:
        html.append(
            "<tr>"
            f"<td>{esc(r.ts.isoformat())}</td>"
            f"<td>{esc(r.event_type)}</td>"
            f"<td>{esc(r.status)}</td>"
            f"<td>{esc(r.symbol)}</td>"
            f"<td>{esc(r.side)}</td>"
            f"<td>{esc(r.qty)}</td>"
            f"<td>{esc(r.reason or '')}</td>"
            "</tr>"
        )
    html.append("</table>")

    html.append("</body></html>")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(html), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--month", required=True, help="YYYY-MM (e.g. 2025-12)")
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    month = str(args.month).strip()

    log_path = _find_trades_log(repo_root)
    reports_dir = repo_root / "Data" / "Reports"
    out_path = reports_dir / f"tca_{month.replace('-', '_')}.html"

    if log_path is None:
        # Still write a report explaining what happened
        _write_report(repo_root=repo_root, month=month, out_path=out_path, rows=[])
        print(f"[TCA] log not found. wrote report: {out_path}")
        return

    rows = _read_rows(log_path)
    rows_m = [r for r in rows if r.month == month]

    _write_report(repo_root=repo_root, month=month, out_path=out_path, rows=rows_m)
    print(f"[TCA] read {len(rows_m)} events from {log_path}")
    print(f"[TCA] wrote report: {out_path}")


if __name__ == "__main__":
    main()