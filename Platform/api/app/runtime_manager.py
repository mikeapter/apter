from __future__ import annotations

import json
import os
import signal
import subprocess
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional

from .settings import BOTTRADER_ROOT, RUNTIME_DIR, SCRIPTS_DIR, detect_bot_python_exe


@dataclass
class BotRun:
    bot_id: str
    pid: int
    script: str
    args: List[str]
    log: str
    started_at: float


def _is_windows() -> bool:
    return os.name == "nt"


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        if _is_windows():
            # On Windows, os.kill(pid, 0) works in modern Python for existence checks
            os.kill(pid, 0)
            return True
        else:
            os.kill(pid, 0)
            return True
    except OSError:
        return False


class BotRuntime:
    """
    Manages bot processes + state on disk in Platform/runtime.
    """

    def __init__(self) -> None:
        RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
        self._runs: Dict[str, BotRun] = {}
        self._load_state_files()

    def _state_path(self, bot_id: str) -> Path:
        return RUNTIME_DIR / f"{bot_id}.state.json"

    def _log_path(self, bot_id: str) -> Path:
        return RUNTIME_DIR / f"{bot_id}.log"

    def _load_state_files(self) -> None:
        for p in RUNTIME_DIR.glob("*.state.json"):
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                run = BotRun(**data)
                # Only restore if process still alive
                if _pid_alive(run.pid):
                    self._runs[run.bot_id] = run
            except Exception:
                # Ignore corrupt state
                pass

    def _save_state(self, run: BotRun) -> None:
        self._state_path(run.bot_id).write_text(
            json.dumps(asdict(run), indent=2),
            encoding="utf-8",
        )

    def _clear_state(self, bot_id: str) -> None:
        sp = self._state_path(bot_id)
        if sp.exists():
            try:
                sp.unlink()
            except Exception:
                pass

    def get(self, bot_id: str) -> Optional[BotRun]:
        run = self._runs.get(bot_id)
        if not run:
            return None
        if not _pid_alive(run.pid):
            # stale
            self._runs.pop(bot_id, None)
            self._clear_state(bot_id)
            return None
        return run

    def status(self, bot_id: str) -> dict:
        run = self.get(bot_id)
        if not run:
            return {"bot_id": bot_id, "running": False}
        return {
            "bot_id": run.bot_id,
            "running": True,
            "pid": run.pid,
            "script": run.script,
            "args": run.args,
            "log": run.log,
            "started_at": run.started_at,
        }

    def start(self, bot_id: str, script_rel: str, args: Optional[List[str]] = None) -> dict:
        existing = self.get(bot_id)
        if existing:
            return self.status(bot_id)

        args = args or []

        # Resolve script path safely inside repo/scripts
        script_path = (BOTTRADER_ROOT / script_rel).resolve()
        if not str(script_path).startswith(str(BOTTRADER_ROOT.resolve())):
            raise ValueError("Invalid script path (outside repo).")

        if not script_path.exists():
            raise FileNotFoundError(f"Script not found: {script_path}")

        # Ensure script is inside scripts/ (recommended safety)
        if script_path.parent != SCRIPTS_DIR.resolve():
            raise ValueError(f"Script must live in scripts/: {script_path}")

        python_exe = detect_bot_python_exe()

        log_path = self._log_path(bot_id)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Always run bots from repo root so imports like `from App...` work
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        # Important: ensure repo root is importable
        # If you already use relative imports correctly, this is still helpful.
        env["PYTHONPATH"] = str(BOTTRADER_ROOT) + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")

        # Windows: allow sending CTRL_BREAK_EVENT to the process group if needed
        creationflags = 0
        if _is_windows() and hasattr(subprocess, "CREATE_NEW_PROCESS_GROUP"):
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

        with log_path.open("a", encoding="utf-8") as lf:
            lf.write(f"\n--- START {bot_id} ---\n")
            lf.flush()

            proc = subprocess.Popen(
                [python_exe, str(script_path), *args],
                cwd=str(BOTTRADER_ROOT),
                stdout=lf,
                stderr=subprocess.STDOUT,
                env=env,
                creationflags=creationflags,
            )

        run = BotRun(
            bot_id=bot_id,
            pid=proc.pid,
            script=str(script_path.relative_to(BOTTRADER_ROOT)),
            args=args,
            log=str(log_path),
            started_at=time.time(),
        )
        self._runs[bot_id] = run
        self._save_state(run)
        return self.status(bot_id)

    def stop(self, bot_id: str) -> dict:
        run = self.get(bot_id)
        if not run:
            self._runs.pop(bot_id, None)
            self._clear_state(bot_id)
            return {"bot_id": bot_id, "running": False}

        pid = run.pid

        # Try graceful stop first
        try:
            if _is_windows():
                # Try CTRL_BREAK_EVENT for process group (works if created as new process group)
                try:
                    os.kill(pid, signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
                except Exception:
                    os.kill(pid, signal.SIGTERM)
            else:
                os.kill(pid, signal.SIGTERM)
        except Exception:
            pass

        # Wait a moment
        for _ in range(20):
            if not _pid_alive(pid):
                break
            time.sleep(0.1)

        # Force kill if still alive
        if _pid_alive(pid):
            try:
                if _is_windows():
                    os.kill(pid, signal.SIGTERM)
                else:
                    os.kill(pid, signal.SIGKILL)
            except Exception:
                pass

        self._runs.pop(bot_id, None)
        self._clear_state(bot_id)

        return {"bot_id": bot_id, "running": False}

    def read_log_tail(self, bot_id: str, max_lines: int = 250) -> str:
        run = self.get(bot_id)

        # Even if not running, logs may exist; fall back to runtime log file.
        log_path = self._log_path(bot_id) if not run else Path(run.log)

        if not log_path.exists():
            raise FileNotFoundError("No log file yet")

        lines = log_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        return "\n".join(lines[-max_lines:])
