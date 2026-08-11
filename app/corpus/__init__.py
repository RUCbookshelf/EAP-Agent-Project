"""Corpus & NLP Intelligence department module (Stage 5 + Wave-2 routing).

Additive, read-only Corpus Intelligence foundation: resource registration,
feature contract, feature extraction, reference groups, reference
distributions, and the internal query boundary consumed by Stage 6.
Wave-2 Goal E adds modality-aware corpus product routing (written default;
SECCL spoken + secondary/research_only) in ``app.corpus.routing``.

This module never modifies corpus data and never exposes raw student texts.
"""

from app.corpus.resource import (
    CorpusResourceDescriptor,
    CorpusResourceError,
    compute_manifest_hash,
    get_corpus_resource,
    load_corpus_resource,
)

from app.corpus.routing import (
    L2WritingRouter,
    ResourceClassification,
    ResourceEligibility,
    RoutingResource,
    RoutingResult,
    assess_eligibility,
    classify_resource,
)

__all__ = [
    "CorpusResourceDescriptor",
    "CorpusResourceError",
    "L2WritingRouter",
    "ResourceClassification",
    "ResourceEligibility",
    "RoutingResource",
    "RoutingResult",
    "assess_eligibility",
    "classify_resource",
    "compute_manifest_hash",
    "get_corpus_resource",
    "load_corpus_resource",
]
