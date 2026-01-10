# tests/conftest.py
# Ensure the repository root is on sys.path so imports like `import Core` work

import os
import sys

# repo_root = .../BotTrader (parent of the tests/ directory)
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)
