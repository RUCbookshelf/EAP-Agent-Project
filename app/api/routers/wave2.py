"""Wave-2 API assembly router (Goal PDW2-A-CORE-PERSISTENCE).

This assembly statically imports the Wave-2 sub-routers contributed by later
department Goals from ``app.api.routers.wave2_modules``:

- learner_api (LEARNER Goal PDW2-B-LEARNER-MODEL)
- revision_api (L2 Goal PDW2-C-L2-REVISION-SCAFFOLD)
- personalized_api (L2 Goal PDW2-C-L2-REVISION-SCAFFOLD)

Modules that are not present yet are tolerated (ImportError -> None) so the
assembly mounts cleanly now and picks up each sub-router automatically once
its module lands. Route handlers are owned by the sub-router modules; this
module adds no endpoints of its own.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()

try:
    from app.api.routers.wave2_modules import learner_api
except ImportError:  # not yet contributed (LEARNER Goal PDW2-B)
    learner_api = None

try:
    from app.api.routers.wave2_modules import revision_api
except ImportError:  # not yet contributed (L2 Goal PDW2-C)
    revision_api = None

try:
    from app.api.routers.wave2_modules import personalized_api
except ImportError:  # not yet contributed (L2 Goal PDW2-C)
    personalized_api = None

for _wave2_subrouter in (learner_api, revision_api, personalized_api):
    if _wave2_subrouter is not None and getattr(_wave2_subrouter, "router", None) is not None:
        router.include_router(_wave2_subrouter.router)

