from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    api_key: str
    bottrader_root: Path
    runtime_dir: Path
    bot_python: Path

    # Bot registry (starter)
    # Add more bots here later.
    bots: dict[str, Path]


def load_settings() -> Settings:
    api_key = os.getenv("BOTTRADER_API_KEY", "").strip()

    # root defaults to repo root (two levels up from Platform/api)
    bottrader_root_raw = os.getenv("BOTTRADER_ROOT", "../..").strip()
    bottrader_root = (Path(__file__).resolve().parents[3] / bottrader_root_raw).resolve()

    runtime_dir_raw = os.getenv("BOTTRADER_RUNTIME_DIR", "../runtime").strip()
    runtime_dir = (Path(__file__).resolve().parents[3] / runtime_dir_raw).resolve()

    bot_python_raw = os.getenv("BOT_PYTHON") or os.getenv("BOTTRADER_BOT_PYTHON") or ""
    bot_python_raw = bot_python_raw.strip()
    if bot_python_raw:
        bot_python = Path(bot_python_raw)
    else:
        # fallback to current interpreter
        import sys
        bot_python = Path(sys.executable)

    bots = {
        "opening": (bottrader_root / "opening.py").resolve(),
    }

    return Settings(
        api_key=api_key,
        bottrader_root=bottrader_root,
        runtime_dir=runtime_dir,
        bot_python=bot_python,
        bots=bots,
    )
