export type MarketStatus = "Pre-market" | "Open" | "After-hours" | "Closed";

function getNYTimeParts(d: Date) {
  const fmt = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    hour12: false,
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
  const parts = fmt.formatToParts(d);
  const get = (t: string) => parts.find((p) => p.type === t)?.value ?? "";
  return {
    weekday: get("weekday"),
    hour: parseInt(get("hour"), 10),
    minute: parseInt(get("minute"), 10),
  };
}

export function computeMarketStatus(now = new Date()): {
  status: MarketStatus;
  nextChangeLabel: string;
} {
  const { weekday, hour, minute } = getNYTimeParts(now);

  const isWeekend = weekday === "Sat" || weekday === "Sun";
  if (isWeekend) return { status: "Closed", nextChangeLabel: "Opens Monday 9:30 ET" };

  const t = hour * 60 + minute;
  const pre = 4 * 60;       // 04:00
  const open = 9 * 60 + 30; // 09:30
  const close = 16 * 60;    // 16:00
  const after = 20 * 60;    // 20:00

  if (t >= pre && t < open) return { status: "Pre-market", nextChangeLabel: "Opens 9:30 ET" };
  if (t >= open && t < close) return { status: "Open", nextChangeLabel: "Closes 4:00 ET" };
  if (t >= close && t < after) return { status: "After-hours", nextChangeLabel: "Closes 8:00 ET" };

  return { status: "Closed", nextChangeLabel: "Opens 9:30 ET" };
}
