"""Corpus & NLP Intelligence department module (Stage 5).

Additive, read-only Corpus Intelligence foundation: resource registration,
feature contract, feature extraction, reference groups, reference
distributions, and the internal query boundary consumed by Stage 6.

This module never modifies corpus data and never exposes raw student texts.
"""

from app.corpus.resource import (
    CorpusResourceDescriptor,
    CorpusResourceError,
    compute_manifest_hash,
    get_corpus_resource,
    load_corpus_resource,
)

__all__ = [
    "CorpusResourceDescriptor",
    "CorpusResourceError",
    "compute_manifest_hash",
    "get_corpus_resource",
    "load_corpus_resource",
]
