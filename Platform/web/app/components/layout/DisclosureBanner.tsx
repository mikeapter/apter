"use client";

export function DisclosureBanner() {
  return (
    <div className="w-full border-b border-border bg-panel-2 px-4 py-2">
      <p className="text-[11px] md:text-xs text-muted-foreground tracking-[0.01em]">
        Information is for educational and research purposes only. Not investment advice.
        Apter Financial is not acting as a registered investment adviser.
      </p>
    </div>
  );
}
