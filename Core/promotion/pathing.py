from __future__ import annotations

from pathlib import Path

def find_dir(base: Path, candidates: list[str]) -> Path:
    for name in candidates:
        p = base / name
        if p.exists() and p.is_dir():
            return p
    # fallback: first candidate
    return base / candidates[0]

def config_dir(repo_root: Path) -> Path:
    return find_dir(repo_root, ["config", "Config"])

def strategies_dir(repo_root: Path) -> Path:
    return find_dir(repo_root, ["strategies", "Strategies"])
