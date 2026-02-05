from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


def _repo_root() -> Path:
    """
    File path:
      Platform/api/app/services/bot_runtime.py
    parents:
      services -> app -> api -> Platform -> <REPO ROOT>
    """
    return Path(__file__).resolve().parents[4]


def _runtime_dir() -> Path:
    """
    Used by system.py (/config).
    Must be a function because system.py calls _runtime_dir().
    """
    d = _repo_root() / "Platform" / "runtime"
    d.mkdir(parents=True, exist_ok=True)
    return d


def resolve_script_for_bot(bot_id: str) -> str:
    """
    Used by system.py (/config). Returns the script path for a given bot.
    Defaults:
      opening -> scripts/run_opening.py
    Override options:
      BOTTRADER_DEFAULT_SCRIPT
      BOTTRADER_SCRIPT_<BOT_ID> (uppercased, non-alnum -> _)
    """
    default_script = os.getenv("BOTTRADER_DEFAULT_SCRIPT", "scripts/run_opening.py")

    key = "BOTTRADER_SCRIPT_" + "".join([c if c.isalnum() else "_" for c in bot_id.upper()])
    specific = os.getenv(key)

    if specific:
        return specific

    if bot_id == "opening":
        return os.getenv("BOTTRADER_OPENING_SCRIPT", default_script)

    return default_script


def _bots_file() -> Path:
    return _runtime_dir() / "bots.json"


def _log_file(bot_id: str) -> Path:
    # keep it simple for now: one log per bot
    return _runtime_dir() / f"{bot_id}.log"


def _load_bots() -> Dict[str, Any]:
    p = _bots_file()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_bots(data: Dict[str, Any]) -> None:
    _bots_file().write_text(json.dumps(data, indent=2), encoding="utf-8")


def start_bot(bot_id: str) -> Dict[str, Any]:
    bots = _load_bots()
    if bot_id in bots and bots[bot_id].get("running"):
        return bots[bot_id]

    root = _repo_root()
    script = resolve_script_for_bot(bot_id)

    log_path = _log_file(bot_id)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.touch(exist_ok=True)

    # Use the same python running FastAPI (venv-safe)
    py = sys.executable

    # Always run from repo root so "scripts/..." resolves correctly
    cmd = [py, "-u", script]

    with open(log_path, "a", encoding="utf-8") as lf:
        proc = subprocess.Popen(
            cmd,
            cwd=str(root),
            stdout=lf,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
        )

    bots[bot_id] = {
        "pid": proc.pid,
        "script": script,
        "cmd": cmd,
        "cwd": str(root),
        "running": True,
        "started_at": datetime.utcnow().isoformat() + "Z",
        "log_file": str(log_path),
    }
    _save_bots(bots)
    return bots[bot_id]


def stop_bot(bot_id: str) -> Optional[Dict[str, Any]]:
    bots = _load_bots()
    bot = bots.get(bot_id)
    if not bot:
        return None

    pid = bot.get("pid")
    if pid:
        try:
            if os.name == "nt":
                # Prefer taskkill on Windows
                subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], check=False)
            else:
                os.kill(pid, signal.SIGTERM)
        except Exception:
            pass

    bots.pop(bot_id, None)
    _save_bots(bots)
    return {"stopped": True, "bot_id": bot_id}


def get_status(bot_id: str) -> Dict[str, Any]:
    bots = _load_bots()
    bot = bots.get(bot_id)
    if not bot:
        return {"running": False, "pid": None, "script": None}

    return {
        "running": True,
        "pid": bot.get("pid"),
        "script": bot.get("script"),
        "started_at": bot.get("started_at"),
        "log_file": bot.get("log_file"),
    }


def get_logs(bot_id: str = "opening", tail: int = 5000) -> str:
    p = _log_file(bot_id)
    if not p.exists():
        return "(no logs yet)"
    txt = p.read_text(encoding="utf-8", errors="replace")
    return txt[-tail:]
