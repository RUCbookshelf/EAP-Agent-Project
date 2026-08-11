"""Wave-2 Student Experience integration layer (Goal PDW2-D-UX-STUDENT).

UX-owned adapter surface for the Wave-2 API contracts that land at
integration (revision_api / personalized_api / learner_api under
/api/v1/wave2/). This module family implements:

- ``client.py``  HTTP client against the documented Wave-2 endpoints with
  fail-closed availability classification.
- ``mock.py``    contract-shaped local mock backend/client for tests and
  demos; never fabricates history for learners without stored history.
- ``views.py``   student-safe view mapping (allowlist; raw technical
  internals never reach student surfaces by default).
- ``gateway.py`` UI facade: Wave-2 first, graceful degradation to the
  existing writing/feedback flow while the Wave-2 endpoints are
  unavailable (they land at integration).
"""

from __future__ import annotations