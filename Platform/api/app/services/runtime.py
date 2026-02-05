from __future__ import annotations

import os
import signal
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class BotStatus:
    running: bool
    pid: Optional[int]
    script: str


def _api_root() -> Path:
    # Platform/api/app/services/runtime.py -> parents[2] == Platform/api
    return Path(__file__).resolve().parents[2]


def _resolve_root() -> Path:
    """
    BOTTRADER_ROOT is stored like ../.. relative to Platform/api by default.
    Resolve it into an absolute path.
    """
    api_root = _api_root()
    raw = os.getenv("BOTTRADER_ROOT", "../..")
    return (api_root / raw).resolve()


def _runtime_dir() -> Path:
    api_root = _api_root()
    raw = os.getenv("BOTTRADER_RUNTIME_DIR", "../runtime")
    p = (api_root / raw).resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def _bot_python() -> Path:
    api_root = _api_root()
    raw = os.getenv("BOT_PYTHON", "")
    if raw.strip():
        return (api_root / raw).resolve() if not Path(raw).is_absolute() else Path(raw)
    # fallback: run with current interpreter
    return Path(os.sys.executable)


def _pid_file(bot_id: str) -> Path:
    return _runtime_dir() / f"{bot_id}.pid"


def _log_file(bot_id: str) -> Path:
    return _runtime_dir() / f"{bot_id}.log"


def _bot_script(bot_id: str) -> Path:
    """
    Map bot_id -> script path inside BotTrader repo root.
    Keep it simple for now: opening -> opening.py at repo root.
    """
    root = _resolve_root()

    if bot_id == "opening":
        return (root / "opening.py").resolve()

    # Add more bots later
    return (root / f"{bot_id}.py").resolve()


def status(bot_id: str) -> BotStatus:
    script_path = _bot_script(bot_id)

    pf = _pid_file(bot_id)
    if not pf.exists():
        return BotStatus(running=False, pid=None, script=str(script_path))

    try:
        pid = int(pf.read_text(encoding="utf-8").strip())
    except Exception:
        pf.unlink(missing_ok=True)
        return BotStatus(running=False, pid=None, script=str(script_path))

    # Check if PID is alive (Windows-safe: just try signal 0 on POSIX; on Windows use OpenProcess?).
    # We'll do a simple approach: attempt to send signal 0 where supported; otherwise assume running.
    running = True
    try:
        if os.name != "nt":
            os.kill(pid, 0)
    except Exception:
        running = False

    if not running:
        pf.unlink(missing_ok=True)
        return BotStatus(running=False, pid=None, script=str(script_path))

    return BotStatus(running=True, pid=pid, script=str(script_path))


def start(bot_id: str) -> BotStatus:
    st = status(bot_id)
    if st.running:
        return st

    script_path = _bot_script(bot_id)
    if not script_path.exists():
        raise FileNotFoundError(f"Bot script not found: {script_path}")

    py = _bot_python()
    lf = _log_file(bot_id)

    # Ensure log file exists
    lf.parent.mkdir(parents=True, exist_ok=True)
    log_handle = open(lf, "a", encoding="utf-8")

    # Start detached-ish process writing to log
    # Windows: creationflags for new process group so we can terminate easier if needed later
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]

    p = subprocess.Popen(
        [str(py), str(script_path)],
        cwd=str(_resolve_root()),
        stdout=log_handle,
        stderr=log_handle,
        stdin=subprocess.DEVNULL,
        creationflags=creationflags,
    )

    _pid_file(bot_id).write_text(str(p.pid), encoding="utf-8")
    return status(bot_id)


def stop(bot_id: str) -> BotStatus:
    st = status(bot_id)
    if not st.running or not st.pid:
        return st

    pid = st.pid

    try:
        if os.name == "nt":
            # CTRL_BREAK_EVENT requires process group; we created one above.
            os.kill(pid, signal.SIGBREAK)  # type: ignore[attr-defined]
        else:
            os.kill(pid, signal.SIGTERM)
    except Exception:
        pass

    # Clean PID file regardless (best-effort)
    _pid_file(bot_id).unlink(missing_ok=True)
    return status(bot_id)


def tail_logs(bot_id: str, n: int = 50) -> list[str]:
    lf = _log_file(bot_id)
    if not lf.exists():
        return []

    try:
        lines = lf.read_text(encoding="utf-8", errors="replace").splitlines()
        return lines[-max(1, n):]
    except Exception:
        return []
