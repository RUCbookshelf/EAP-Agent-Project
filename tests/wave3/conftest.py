"""Shared WU3 fixtures (real-pipeline adaptive / mini-writing / tutor)."""

from __future__ import annotations

from .test_adaptive_practice import adaptive
from .test_mini_writing import mini
from .test_tutor import tutor_env

__all__ = ["adaptive", "mini", "tutor_env"]
