from _bootstrap import bootstrap
bootstrap()

import sys
from pathlib import Path

# Add BotTrader/ (project root) to Python import path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from App.strategy_governance import StrategyGovernance

if __name__ == "__main__":
    gov = StrategyGovernance(repo_root=ROOT)
    raise SystemExit(gov.print_report())