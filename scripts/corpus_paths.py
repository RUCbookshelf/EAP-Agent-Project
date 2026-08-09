"""Portable path resolution for corpus scripts.

This module provides functions to resolve repository and corpus root paths
in a portable manner, avoiding machine-specific absolute paths.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def get_repo_root() -> Path:
    """Resolve repository root relative to this file's location.
    
    Returns:
        Path to the repository root directory.
    """
    # This file is at scripts/corpus_paths.py
    # Repository root is two levels up
    return Path(__file__).resolve().parent.parent


def get_corpus_root() -> Path:
    """Get corpus root from environment variable.
    
    Returns:
        Path to the SWECCL corpus root.
        
    Raises:
        SystemExit: If CORPUS_ROOT environment variable is not set.
    """
    corpus_root = os.environ.get("CORPUS_ROOT")
    if not corpus_root:
        sys.exit("ERROR: CORPUS_ROOT environment variable not set. "
                 "Please set it to the SWECCL corpus root.")
    return Path(corpus_root)


def get_readiness_out_dir() -> Path:
    """Get output directory for corpus readiness data.
    
    Returns:
        Path to docs/corpus-readiness/sweccl2/data directory.
    """
    repo_root = get_repo_root()
    return repo_root / "docs" / "corpus-readiness" / "sweccl2" / "data"


def get_corpus_prepared() -> Path:
    """Get prepared corpus layer directory.
    
    Returns:
        Path to CORPUS_ROOT/PREPARED directory.
    """
    return get_corpus_root() / "PREPARED"
