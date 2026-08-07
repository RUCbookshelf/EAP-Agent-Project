"""Reproducible corpus-readiness pipeline (WU1-WU9).

Usage:
  python scripts/corpus_readiness/run_all.py

Deterministic, idempotent, read-only over the corpus; derived UTF-8 layer is
regenerated from sources each run (overwrites PREPARED/utf8 deterministically).
Run with the bundled Python 3.12+.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable
STEPS = [
    ("01_inventory.py", "physical inventory + sha256 + encoding detection"),
    ("02_encoding.py", "encoding audit + derived UTF-8 layer + derived_manifest"),
    ("03_manifest.py", "canonical manifest + metadata coverage"),
    ("04_pairing.py", "RAW/LEMMA/TAGGED pairing audit"),
    ("05_quality.py", "quality/duplicate/exclusion audit"),
    ("06_composition.py", "composition + documentation-vs-physical"),
    ("07_reference_groups.py", "reference-group candidates"),
    ("08_features.py", "feature feasibility registry"),
    ("09_leakage.py", "evaluation/leakage plan"),
]


def main() -> int:
    started = time.time()
    for script, label in STEPS:
        print(f"\n=== {script}: {label} ===", flush=True)
        r = subprocess.run([PY, "-X", "utf8", str(HERE / script)])
        if r.returncode != 0:
            print(f"FAILED: {script} (exit {r.returncode})", file=sys.stderr)
            return r.returncode
    print(f"\nAll steps completed in {time.time() - started:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
