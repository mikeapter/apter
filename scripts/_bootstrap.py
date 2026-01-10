# scripts/_bootstrap.py
from __future__ import annotations

import sys
from pathlib import Path


def bootstrap() -> None:
    """
    Ensure BotTrader/BotTrader is on sys.path so `import Core...` works whether you run:
      - python scripts/run_system.py
      - python -m scripts.run_system
    """
    root = Path(__file__).resolve().parents[1]  # .../BotTrader/BotTrader
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
