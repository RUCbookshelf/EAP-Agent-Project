"""Wave-3 WU3 L2 Adaptive Practice + Proactive Tutor domain (Goal
PDW3-WU3-L2-ADAPTIVE-PRACTICE-TUTOR-20260812).

Additive L2 domain behavior over the existing shared application contracts:

- AdaptivePracticeService: qualified activity recommendation from the
  existing practice capability with a deterministic, explainable default and
  explicit learner choice; provenance and deterministic evaluation criteria
  are preserved and never fabricated.
- MiniWritingService: bounded mini-writing that re-enters the EXISTING
  Writing Intelligence pipeline (no disconnected analysis or essay-generation
  service).
- ProactiveTutorService: consented, history-aware Tutor orchestration
  (recommendation, accept, decline, due-item, history-grounded,
  insufficient-history, positive-observation) with side-effect-safe decline
  and unavailable states.

Every composed output is observation-only: practice/review evidence stays
distinct from authentic-writing observation, and neither is converted into
an outcome, rank, or causal claim.
"""

from __future__ import annotations

from app.l2.wave3.adaptive_practice import AdaptivePracticeService
from app.l2.wave3.mini_writing import MiniWritingService
from app.l2.wave3.tutor import ProactiveTutorService

__all__ = [
    "AdaptivePracticeService",
    "MiniWritingService",
    "ProactiveTutorService",
]
