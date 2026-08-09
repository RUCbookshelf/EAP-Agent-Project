"""Existing-runtime agent capability execution v1 (CORE, Product Delivery Wave 1).

Additive package implementing the qualified ADR-01/02/08 contracts inside the
existing single-process application:

* ``manifest.py`` — capability manifest metadata (identity/version/owner/
  domain-eligibility/scope/data-access/source/enablement/audit);
* ``registry.py`` — additive-only, versioned registry with duplicate
  registration rejection (ADR-02), federating existing authoritative domain
  entry points read-only;
* ``executor.py`` — synchronous in-process executor with dispatch-time
  eligibility/scope checks, explicit ``success`` / ``unavailable`` /
  ``ineligible`` / ``error`` states, exception isolation, and provenance/audit
  records;
* ``capabilities.py`` — the two real v1 domain capabilities (L2 task-type
  classification and governed corpus_query);
* ``bootstrap.py`` — default wiring (``create_runtime``).

No parallel runtime, orchestrator, event bus, second composition root, or
runtime database is introduced.  DeepTutor source was used only as a
read-only mechanism reference (manifest-first registration, dispatch-time
authorization, structured capability results); no code was copied.
"""

from __future__ import annotations

from app.runtime.bootstrap import create_runtime
from app.runtime.capabilities import (
    GovernedCorpusQueryCapability,
    L2TaskTypeClassifierCapability,
)
from app.runtime.errors import (
    CapabilityDeniedError,
    CapabilityNotFoundError,
    CapabilityRegistrationError,
    CapabilityRequestError,
    CapabilityUnavailableError,
    ManifestValidationError,
)
from app.runtime.executor import (
    RUNTIME_PROVENANCE_ID,
    STATUS_ERROR,
    STATUS_INELIGIBLE,
    STATUS_SUCCESS,
    STATUS_UNAVAILABLE,
    CapabilityExecutor,
    CapabilityResult,
)
from app.runtime.manifest import CapabilityManifest, validate_manifest
from app.runtime.registry import CapabilityRegistry, RegisteredCapability

__all__ = [
    "CapabilityDeniedError",
    "CapabilityExecutor",
    "CapabilityManifest",
    "CapabilityNotFoundError",
    "CapabilityRegistrationError",
    "CapabilityRequestError",
    "CapabilityResult",
    "CapabilityRegistry",
    "CapabilityUnavailableError",
    "GovernedCorpusQueryCapability",
    "L2TaskTypeClassifierCapability",
    "ManifestValidationError",
    "RUNTIME_PROVENANCE_ID",
    "RegisteredCapability",
    "STATUS_ERROR",
    "STATUS_INELIGIBLE",
    "STATUS_SUCCESS",
    "STATUS_UNAVAILABLE",
    "create_runtime",
    "validate_manifest",
]
