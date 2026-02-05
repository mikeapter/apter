"use client";

import React, { useEffect, useRef } from "react";

export default function MobileSidebar({
  open,
  onClose,
  children,
}: {
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
}) {
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    if (open) document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 md:hidden">
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />
      <div
        ref={panelRef}
        className="absolute left-0 top-0 h-full w-80 max-w-[90vw] border-r border-white/10 bg-black/90 backdrop-blur"
      >
        <div className="flex items-center justify-between px-4 py-3">
          <div className="text-sm font-semibold text-white">BotTrader</div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-xs text-white"
          >
            Close
          </button>
        </div>
        <div className="h-[calc(100%-52px)] overflow-auto">{children}</div>
      </div>
    </div>
  );
}
