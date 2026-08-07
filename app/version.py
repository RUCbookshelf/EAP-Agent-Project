"""Shared platform version identity (D-20, D-29 scope).

This module is the SINGLE SOURCE OF TRUTH for the application-level
platform identity: application version, API version, and database
migration version.  Every consumer that reports or records the
application version must import from here.

Version rationale
-----------------
``PLATFORM_APPLICATION_VERSION`` is set to ``"0.9.7-d"`` to correct
stale ``0.8.0`` / ``0.8.2`` literals that no longer reflect the
closed v0.9.7-D baseline.  The trailing ``-d`` tag marks the
development / single-sourcing integration pass.

Out of scope (D-29)
-------------------
Subsystem version streams remain **independent** and are NOT
centralised here:

- ``spacy-analyzer-v0.8.0``
- ``feedback-prompt-v0.7.1``
- ``diagnostic-calibration-v0.6.1``
- ``structured-feedback-v0.7.1``
- journey / configuration / metric-registry / calf-construct-registry
- corpus-features / reference-groups / reference-distributions

Any change to a subsystem version must happen in its own module and
must not be confused with a platform version bump.
"""
from __future__ import annotations


# -- Platform application identity ---------------------------------
PLATFORM_APPLICATION_VERSION: str = "0.9.7-d"

# -- API surface version --------------------------------------------
PLATFORM_API_VERSION: str = "v1"

# -- Database migration version -------------------------------------
# This must match migrations.LATEST_MIGRATION_VERSION; drift tests
# enforce the invariant.
PLATFORM_DATABASE_MIGRATION_VERSION: int = 13

