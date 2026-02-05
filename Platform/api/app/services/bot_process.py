from __future__ import annotations

import os
import signal
import subprocess
from pathlib import Path
from typing import Optional, Tuple


def _runtime_dir() -> Path:
    # Default: Platform/runtime (relative to Platform/api)
    # Your API usually runs from Platform/api, so ../runtime is correct.
    runtime = Path(os.environ.get("BOTTRADER_RUNTIME_DIR", "../runtime")).resolve()
    runtime.mkdir(parents=True, exist_ok=True)
    return runtime


def _logs_dir() -> Path:
    logs = _runtime_dir() / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    return logs


def pid_file(bot_id: str) -> Path:
    return _runtime_dir() / f"{bot_id}.pid"


def log_file(bot_id: str) -> Path:
    return _logs_dir() / f"{bot_id}.log"


def is_running(bot_id: str) -> Tuple[bool, Optional[int]]:
    pf = pid_file(bot_id)
    if not pf.exists():
        return False, None

    try:
        pid = int(pf.read_text(encoding="utf-8").strip())
    except Exception:
        # corrupt pid file
        try:
            pf.unlink()
        except Exception:
            pass
        return False, None

    # Check if process exists
    try:
        os.kill(pid, 0)
        return True, pid
    except OSError:
        # stale pid
        try:
            pf.unlink()
        except Exception:
            pass
        return False, pid


def start_bot(bot_id: str, script_path: str, python_exe: str) -> dict:
    running, pid = is_running(bot_id)
    if running:
        return {"ok": True, "message": "already running", "pid": pid, "script": script_path}

    lf_path = log_file(bot_id)
    # Ensure file exists so logs endpoint works immediately after start
    lf_path.parent.mkdir(parents=True, exist_ok=True)
    lf_path.touch(exist_ok=True)

    # Windows note:
    # Use CREATE_NEW_PROCESS_GROUP so we can send signals cleanly if needed
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]

    with open(lf_path, "a", encoding="utf-8", errors="ignore") as lf:
        proc = subprocess.Popen(
            [python_exe, script_path],
            stdout=lf,
            stderr=subprocess.STDOUT,
            cwd=str(Path(script_path).resolve().parent),
            creationflags=creationflags,
        )

    pid_file(bot_id).write_text(str(proc.pid), encoding="utf-8")
    return {"ok": True, "message": "started", "pid": proc.pid, "script": script_path, "log_file": str(lf_path)}


def stop_bot(bot_id: str) -> dict:
    running, pid = is_running(bot_id)
    if not pid:
        return {"ok": True, "message": "not running", "pid": None}

    # If not running, clean pid file and return
    if not running:
        try:
            pid_file(bot_id).unlink()
        except Exception:
            pass
        return {"ok": True, "message": "not running (stale pid cleaned)", "pid": pid}

    try:
        if os.name == "nt":
            # On Windows, try CTRL_BREAK_EVENT if in new process group; fallback to terminate
            try:
                os.kill(pid, signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
            except Exception:
                os.kill(pid, signal.SIGTERM)
        else:
            os.kill(pid, signal.SIGTERM)
    except Exception as e:
        return {"ok": False, "message": f"failed to stop: {e}", "pid": pid}

    try:
        pid_file(bot_id).unlink()
    except Exception:
        pass

    return {"ok": True, "message": "stopped", "pid": pid}


def read_log_tail(bot_id: str, max_lines: int = 200) -> str:
    """
    Return the last `max_lines` lines of the bot log.

    IMPORTANT: If the log doesn't exist yet (bot never started), return empty string
    instead of throwing FileNotFoundError (which was causing 500s).
    """
    path = log_file(bot_id)
    if not path.exists():
        return ""

    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

    if not text.strip():
        return ""

    lines = text.splitlines()
    tail = lines[-max_lines:]
    return "\n".join(tail)
