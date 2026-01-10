from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_tree(
    root: Path,
    *,
    include_globs: Tuple[str, ...] = ("*.py", "*.yaml", "*.yml", "*.json"),
    exclude_dirs: Tuple[str, ...] = ("__pycache__", ".pytest_cache", ".git"),
) -> str:
    root = Path(root)
    files: List[Path] = []
    for g in include_globs:
        files.extend(root.rglob(g))
    files = [p for p in files if not any(part in exclude_dirs for part in p.parts)]
    files_sorted = sorted(files, key=lambda p: str(p.relative_to(root)).lower())

    h = hashlib.sha256()
    for p in files_sorted:
        rel = str(p.relative_to(root)).encode("utf-8")
        h.update(rel + b"\n")
        h.update(sha256_file(p).encode("utf-8") + b"\n")
    return h.hexdigest()


def git_commit(repo_root: Path) -> Optional[str]:
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=str(repo_root))
        return out.decode().strip()
    except Exception:
        return None


def pip_freeze() -> List[str]:
    try:
        out = subprocess.check_output([sys.executable, "-m", "pip", "freeze"])
        return [line.strip() for line in out.decode().splitlines() if line.strip()]
    except Exception:
        return []


def env_fingerprint() -> Dict[str, Any]:
    return {
        "python": sys.version.replace("\n", " "),
        "platform": platform.platform(),
        "executable": sys.executable,
        "cwd": os.getcwd(),
    }


def snapshot_configs(repo_root: Path, *, out_dir: Path) -> Dict[str, str]:
    repo_root = Path(repo_root)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    hashes: Dict[str, str] = {}
    for base in ("Config", "config"):
        src = repo_root / base
        if not src.exists():
            continue
        for p in src.rglob("*"):
            if p.is_dir():
                continue
            rel = f"{base}/{p.relative_to(src)}"
            dst = out_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            data = p.read_bytes()
            dst.write_bytes(data)
            hashes[rel] = sha256_bytes(data)
    return hashes


def create_run_bundle(repo_root: Path, *, run_id: str, mode: str, extra: Optional[Dict[str, Any]] = None) -> Path:
    repo_root = Path(repo_root)
    runs_root = repo_root / "Data" / "Runs"
    run_dir = runs_root / str(run_id)
    run_dir.mkdir(parents=True, exist_ok=True)

    configs_hashes = snapshot_configs(repo_root, out_dir=run_dir / "configs")
    config_hash = sha256_bytes(json.dumps(configs_hashes, sort_keys=True).encode("utf-8"))
    code_hash = sha256_tree(repo_root, include_globs=("*.py",), exclude_dirs=("__pycache__", ".pytest_cache", ".git"))

    manifest = {
        "run_id": str(run_id),
        "mode": str(mode).upper(),
        "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time())),
        "git_commit": git_commit(repo_root),
        "config_hash": config_hash,
        "code_hash": code_hash,
        "configs": configs_hashes,
        "env": env_fingerprint(),
        "dependencies": pip_freeze(),
        "extra": extra or {},
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return run_dir
