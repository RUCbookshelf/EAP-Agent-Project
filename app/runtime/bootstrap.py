"""Default wiring for the existing-runtime capability execution v1 package.

``create_runtime`` is a plain synchronous composition helper (not a second
composition root): it builds a fresh additive registry, registers the two
real v1 capabilities, and returns the registry plus one executor.  Callers
may inject a ``CorpusIntelligence`` instance or a pre-built registry for
test isolation.
"""

from __future__ import annotations

from app.corpus.intelligence import CorpusIntelligence, create_intelligence
from app.runtime.capabilities import (
    GovernedCorpusQueryCapability,
    L2TaskTypeClassifierCapability,
)
from app.runtime.executor import CapabilityExecutor
from app.runtime.registry import CapabilityRegistry


def create_runtime(
    *,
    intelligence: CorpusIntelligence | None = None,
    registry: CapabilityRegistry | None = None,
) -> tuple[CapabilityRegistry, CapabilityExecutor]:
    """Register the v1 capability set and return ``(registry, executor)``."""
    reg = registry if registry is not None else CapabilityRegistry()
    classifier = L2TaskTypeClassifierCapability()
    reg.register(classifier.manifest, classifier)
    corpus = GovernedCorpusQueryCapability(
        intelligence=intelligence if intelligence is not None else create_intelligence()
    )
    reg.register(corpus.manifest, corpus)
    return reg, CapabilityExecutor(reg)


__all__ = ["create_runtime"]
