from __future__ import annotations

import runpy
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
runpy.run_path(
    str(Path(__file__).with_name("capture_prechange_fresh_database.py")),
    run_name="__main__",
)
