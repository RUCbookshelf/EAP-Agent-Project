from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
source = Path(__file__).with_name("capture_prechange_fresh_database.py")
spec = importlib.util.spec_from_file_location("v095e_fresh_database_capture", source)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.OUTPUT = Path(__file__).with_name("postchange_fresh_database.json")
module.main()
