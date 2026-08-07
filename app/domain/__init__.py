"""Domain and language discriminator package for the shared platform core.

Provides closed-set Domain and Language enumerations, server-side
derivation policy, advisory validation, domain-scope validation,
and the submission ancestry/domain resolver.

References: D-01, D-17, D-21, D-22, D-23, D-28, D-31, D-36.
"""

from app.domain.domain import Domain, Language
from app.domain.attribution import derive_attribution, validate_advisory
from app.domain.validation import validate_domain_scope
from app.domain.resolver import (
    DomainError,
    AncestryRecord,
    AncestryFetchProtocol,
    SubmissionDomainResolver,
    same_domain,
    get_table_family,
    get_registry,
)

__all__ = [
    "Domain",
    "Language",
    "derive_attribution",
    "validate_advisory",
    "validate_domain_scope",
    "DomainError",
    "AncestryRecord",
    "AncestryFetchProtocol",
    "SubmissionDomainResolver",
    "same_domain",
    "get_table_family",
    "get_registry",
]
