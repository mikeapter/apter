"use client";

import { useDashboardData } from "../../providers/DashboardDataProvider";
import { SystemAssessmentPanel } from "../../components/dashboard/SystemAssessmentPanel";
import { SignalMatrixTable } from "../../components/dashboard/SignalMatrixTable";
import { RiskDiagnosticsPanel } from "../../components/dashboard/RiskDiagnosticsPanel";
import { SystemHistoryPanel } from "../../components/dashboard/SystemHistoryPanel";

export default function DashboardView() {
  const { data } = useDashboardData();

  return (
    <div className="space-y-4">
      {/* Top row: Assessment (L) | Signal Matrix (C) | Diagnostics (R) */}
      <div className="grid gap-3 lg:grid-cols-12">
        <div className="lg:col-span-4">
          <SystemAssessmentPanel lines={data.systemAssessment} />
        </div>

        <div className="lg:col-span-5">
          <SignalMatrixTable rows={data.signals} />
        </div>

        <div className="lg:col-span-3">
          <RiskDiagnosticsPanel items={data.diagnostics} />
        </div>
      </div>

      {/* Bottom: System History */}
      <SystemHistoryPanel history={data.history} />
    </div>
  );
}
