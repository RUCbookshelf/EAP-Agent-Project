"""Closed-set domain and language enumerations.

Domain vocabulary (D-22):
  - l2: L2 English writing feedback (default, only functional domain)
  - academic: Academic writing (reserved, NOT functional in H1)

Language vocabulary (D-28):
  - en: English submission language (only verified pipeline language).

legacy_unclassified is task_type semantics (D-22), NOT a domain value.
"""

from __future__ import annotations

from enum import Enum


class Domain(str, Enum):
    """Closed-set product domain vocabulary.

    l2 is the default and only functional domain.  ``academic`` is
    reserved for future use and must NOT be exposed as a functioning
    product domain in H1.
    """

    L2 = "l2"
    ACADEMIC = "academic"


class Language(str, Enum):
    """Closed-set submission language vocabulary.

    ``en`` is the only verified pipeline language in H1.  Distinct from
    UI locale and learner L1.
    """

    EN = "en"


# --- Constants ---------------------------------------------------------------

DEFAULT_DOMAIN: Domain = Domain.L2
DEFAULT_LANGUAGE: Language = Language.EN

VALID_DOMAINS: frozenset[str] = frozenset(d.value for d in Domain)
VALID_LANGUAGES: frozenset[str] = frozenset(l.value for l in Language)
