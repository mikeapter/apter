# BotTrader

This repo is organized so **no `.py` files live in the project root**. Everything is grouped into folders.

## Folder map

- `Core/` — core “engine” modules (risk gates, regime engine, monitoring, promotion, signals, etc.)
- `App/` — glue/entry-facing modules (executors, guardrails, rules, data sources, planners)
- `Config/` — YAML + state JSON files
- `Strategies/` — strategy artifacts (opening playbook, approvals, backtest adapters, etc.)
- `Data/` — sample / local data inputs
- `scripts/` — runnable entrypoints (system runs, opening runs, demos)
- `tests/` — pytest tests (unit tests live under `tests/unit/`)
- `tools/` — manual runners and “testing rules” scripts

## How to run

From the repo root:

```bash
python scripts/run_system.py
python scripts/run_opening.py
```

Those scripts call `scripts/_bootstrap.py` to ensure the project root is on `sys.path`
(so imports like `from Core...` and `from App...` work).

## How to test

```bash
pytest
```

`pytest.ini` is configured to look under `tests/`.
