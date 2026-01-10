from __future__ import annotations
from _bootstrap import bootstrap
bootstrap()


from pathlib import Path

from Core.monitoring.monitoring_manager import MonitoringManager


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    monitor = MonitoringManager(repo_root=root, config_path=root / "Config" / "monitoring.yaml")

    # 1) Load (should not crash even if empty)
    df = monitor.tca.load_events()
    print(f"[MONITOR TEST] events_rows={len(df)} trade_log={monitor.trade_log_path}")

    # 2) Evaluate degradation (OK if no data)
    action = monitor.check_and_apply_degradation()
    print(f"[MONITOR TEST] degradation={action.level} reason={action.reason} details={action.details}")

    # 3) Try monthly report (writes html)
    out = monitor.write_monthly_tca_report()
    print(f"[MONITOR TEST] wrote report: {out}")


if __name__ == "__main__":
    main()