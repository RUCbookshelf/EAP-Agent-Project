"""Corpus Intelligence error taxonomy (read-only boundary)."""


class CorpusIntelligenceError(Exception):
    """Base error for the Corpus Intelligence boundary."""


class CorpusResourceError(CorpusIntelligenceError):
    """Resource registration/verification failure."""


class CorpusUnavailableError(CorpusIntelligenceError):
    """Requested corpus intelligence content is not available."""


class CorpusInvalidRequestError(CorpusIntelligenceError):
    """The request itself is invalid (unknown id, unsupported group, ...)."""
