from __future__ import annotations

import sys
from _bootstrap import bootstrap

bootstrap()


def main() -> int:
    """
    Legacy runner kept for compatibility.

    This repo is SIGNAL-ONLY.
    Redirect to: scripts/run_opening_tool.py
    """
    from scripts.run_opening_tool import _main as tool_main

    # preserve CLI args
    sys.argv = ["run_opening_tool.py"] + sys.argv[1:]
    return int(tool_main())


if __name__ == "__main__":
    raise SystemExit(main())
