from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict


def _parse_env_file(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if not k:
            continue
        out[k] = v
    return out


def bootstrap() -> Path:
    """Ensure repo root is on sys.path and load .env (if present)."""
    here = Path(__file__).resolve()
    repo_root = here.parents[1]

    # sys.path so imports like `from Core...` work
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    # Load .env without requiring python-dotenv
    env_path = repo_root / ".env"
    if env_path.exists():
        kv = _parse_env_file(env_path)
        for k, v in kv.items():
            os.environ.setdefault(k, v)

    return repo_root
