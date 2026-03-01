"use client";

import * as React from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";

type SearchItem = {
  symbol: string;
  name: string;
  exchange?: string;
  type?: string;
  logoUrl?: string;
};

function useDebounce<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = React.useState(value);
  React.useEffect(() => {
    const t = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(t);
  }, [value, delayMs]);
  return debounced;
}

export default function MarketSearch() {
  const router = useRouter();
  const [open, setOpen] = React.useState(false);
  const [q, setQ] = React.useState("");
  const [items, setItems] = React.useState<SearchItem[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [activeIndex, setActiveIndex] = React.useState(0);
  const debouncedQ = useDebounce(q, 150);

  React.useEffect(() => {
    let canceled = false;

    async function run() {
      const query = debouncedQ.trim();
      if (!open) return;

      if (query.length === 0) {
        setItems([]);
        setLoading(false);
        return;
      }

      setLoading(true);
      try {
        const res = await fetch(
          `/api/market/search?q=${encodeURIComponent(query)}`
        );
        const data = await res.json();
        if (!res.ok) throw new Error(data?.error ?? "Search failed");
        if (!canceled) {
          setItems(Array.isArray(data) ? data : []);
          setActiveIndex(0);
        }
      } catch {
        if (!canceled) setItems([]);
      } finally {
        if (!canceled) setLoading(false);
      }
    }

    run();
    return () => {
      canceled = true;
    };
  }, [debouncedQ, open]);

  function selectItem(item: SearchItem | undefined) {
    if (!item) return;
    setOpen(false);
    setQ("");
    setItems([]);
    router.push(`/stocks/${item.symbol}`);
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!open) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, Math.max(items.length - 1, 0)));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      selectItem(items[activeIndex]);
    } else if (e.key === "Escape") {
      e.preventDefault();
      setOpen(false);
    }
  }

  return (
    <div className="relative w-full max-w-xl">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-white/40 pointer-events-none" />
        <input
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onBlur={() => {
            // delay close so click can register
            window.setTimeout(() => setOpen(false), 120);
          }}
          onKeyDown={onKeyDown}
          placeholder="Search ticker or company..."
          className="w-full rounded-lg bg-white/5 border border-white/10 pl-9 pr-4 py-2 text-sm text-white placeholder:text-white/40 outline-none focus:border-white/20"
        />
      </div>

      {open && q.trim().length > 0 && (
        <div className="absolute z-50 mt-2 w-full rounded-xl border border-white/10 bg-[#06102E] shadow-2xl overflow-hidden">
          <div className="px-3 py-2 text-xs text-white/50 border-b border-white/10">
            {loading
              ? "Searching..."
              : items.length
                ? "Top matches"
                : "No results"}
          </div>
          <ul className="max-h-80 overflow-auto">
            {items.map((it, idx) => (
              <li
                key={`${it.symbol}-${idx}`}
                onMouseDown={(e) => e.preventDefault()}
                onClick={() => selectItem(it)}
                className={[
                  "flex items-center gap-3 px-3 py-2 cursor-pointer",
                  idx === activeIndex ? "bg-white/10" : "bg-transparent",
                  "hover:bg-white/10",
                ].join(" ")}
              >
                <div className="h-7 w-7 rounded bg-white/10 overflow-hidden flex items-center justify-center shrink-0">
                  {it.logoUrl ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={it.logoUrl}
                      alt=""
                      className="h-7 w-7 object-contain"
                      loading="lazy"
                    />
                  ) : (
                    <span className="text-[10px] text-white/50">&mdash;</span>
                  )}
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-white">
                      {it.symbol}
                    </span>
                    {it.exchange ? (
                      <span className="text-[11px] text-white/50">
                        {it.exchange}
                      </span>
                    ) : null}
                  </div>
                  <div className="truncate text-xs text-white/60">
                    {it.name}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
