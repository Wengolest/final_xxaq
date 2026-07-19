"""CLI entry: python -m runners.run_agenteval_bundle --bundle ..."""

from __future__ import annotations

import sys
from pathlib import Path

PLATFORM_ROOT = Path(__file__).resolve().parent.parent
if str(PLATFORM_ROOT) not in sys.path:
    sys.path.insert(0, str(PLATFORM_ROOT))

from agenteval_executor.execute import main

if __name__ == "__main__":
    main()
