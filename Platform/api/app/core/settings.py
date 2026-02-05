from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv


def _try_load_dotenv():
    """
    Loads Platform/api/.env if present.
    """
    # This file lives at Platform/api/app/core/settings.py
    # -> parents: core -> app -> api
    api_dir = Path(__file__).resolve().parents[2]
    env_path = api_dir / ".env"
    if env_path.exists():
        load_dotenv(env_path)


_try_load_dotenv()


def repo_root() -> Path:
    """
    Prefer explicit env var; otherwise infer:
    Platform/api/app/core/settings.py -> .../Platform/api/app/core
    -> parents[3] should be BotTrader repo root
    """
    explicit = os.getenv("BOTTRADER_REPO_ROOT")
    if explicit:
        return Path(explicit).expanduser().resolve()

    # core -> app -> api -> Platform -> BotTraderRoot
    return Path(__file__).resolve().parents[4]


def config_dir() -> Path:
    explicit = os.getenv("BOTTRADER_CONFIG_DIR")
    if explicit:
        return Path(explicit).expanduser().resolve()
    return repo_root() / "Config"


def runtime_dir() -> Path:
    explicit = os.getenv("BOTTRADER_RUNTIME_DIR")
    if explicit:
        p = Path(explicit).expanduser().resolve()
    else:
        p = repo_root() / "Platform" / "runtime"
    p.mkdir(parents=True, exist_ok=True)
    return p


def bot_registry() -> Dict[str, Path]:
    """
    Minimal registry for now:
    - bot_id -> script path
    Update as you add more bots.
    """
    root = repo_root()

    # Your screenshots show opening.py at repo root.
    return {
        "opening": root / "opening.py",
    }
