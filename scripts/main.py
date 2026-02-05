from __future__ import annotations

import sys
from _bootstrap import bootstrap

bootstrap()


def main() -> int:
    """
    Legacy entrypoint kept for safety.
    Runs ONE signals cycle.
    """
    from scripts.run_opening_tool import _main as tool_main
    sys.argv = ["run_opening_tool.py", "--once"]
    return int(tool_main())


if __name__ == "__main__":
    raise SystemExit(main())
