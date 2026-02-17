"use client";

import { COMPLIANCE } from "../../lib/compliance";

function gradeColor(grade: number): string {
  if (grade <= 3) return "border-risk-off/40 text-risk-off";
  if (grade <= 7) return "border-risk-neutral/40 text-risk-neutral";
  return "border-risk-on/40 text-risk-on";
}

export function GradeBadge({ grade }: { grade: number }) {
  const clamped = Math.max(1, Math.min(10, Math.round(grade)));

  return (
    <span
      className={`bt-chip ${gradeColor(clamped)} cursor-help`}
      title={COMPLIANCE.GRADE_TOOLTIP}
    >
      <span className="font-semibold">{clamped}</span>
      <span className="text-[10px]">/10</span>
    </span>
  );
}
