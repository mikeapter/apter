from _bootstrap import bootstrap
bootstrap()

import pytest
import sys

if __name__ == "__main__":
    raise SystemExit(pytest.main(["-q", "Testing Rules/test_data_sources_failover.py"]))