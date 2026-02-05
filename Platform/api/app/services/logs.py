from __future__ import annotations

from pathlib import Path


def tail_lines(path: Path, n: int = 50) -> list[str]:
    if n <= 0:
        return []

    if not path.exists():
        return []

    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return lines[-n:]
    except Exception:
        return []
