"""Wave-2 API assembly router (Goal PDW2-A-CORE-PERSISTENCE; F-1 shared store).

This assembly statically imports the Wave-2 sub-routers contributed by later
department Goals from ``app.api.routers.wave2_modules``:

- learner_api (LEARNER Goal PDW2-B-LEARNER-MODEL)
- revision_api (L2 Goal PDW2-C-L2-REVISION-SCAFFOLD)
- personalized_api (L2 Goal PDW2-C-L2-REVISION-SCAFFOLD)

Modules that are not present yet are tolerated (ImportError -> None) so the
assembly mounts cleanly now and picks up each sub-router automatically once
its module lands. Route handlers are owned by the sub-router modules; this
module adds no endpoints of its own.

Wave-2 composition (F-1 repair): this module composes the ONE shared
``SQLiteWave2Repository`` over the composition-root Database and exposes it
at ``app.state.wave2_repository``. Every mounted sub-router carries the
``get_wave2_repository`` dependency, so the revision/personalized/learner
routers resolve the same store (a task created through the revision router
is visible to the personalized and learner routers).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, HTTPException, Request

from app.infrastructure.sqlite.repositories.wave2 import SQLiteWave2Repository

if TYPE_CHECKING:
    from app.database import Database

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


def build_wave2_repository(database: Database) -> SQLiteWave2Repository:
    """Compose the single shared Wave-2 repository over the app Database.

    The repository reuses the composition-root Database's own connection
    manager so the Wave-2 (migration-14) table families live in the one
    application SQLite database alongside every other table family.
    """
    return SQLiteWave2Repository(database._connection_manager)


def get_wave2_repository(request: Request) -> SQLiteWave2Repository:
    """FastAPI dependency resolving the ONE shared Wave-2 repository.

    Composes it from the composition-root Database on first use and caches it
    on ``app.state.wave2_repository`` so every consumer (revision,
    personalized, learner sub-routers) sees the same store instance.
    """
    repository = getattr(request.app.state, "wave2_repository", None)
    if repository is None:
        database = getattr(request.app.state, "repository", None)
        if database is None:
            raise HTTPException(
                status_code=503,
                detail="Wave-2 repository requires the composition-root Database.",
            )
        repository = build_wave2_repository(database)
        request.app.state.wave2_repository = repository
    return repository


# Shared-store dependency wired into every mounted Wave-2 sub-router: one
# SQLiteWave2Repository over the app Database, exposed on app.state.
_WAVE2_SHARED_DEPENDENCIES = [Depends(get_wave2_repository)]

for _wave2_subrouter in (learner_api, revision_api, personalized_api):
    if _wave2_subrouter is not None and getattr(_wave2_subrouter, "router", None) is not None:
        router.include_router(
            _wave2_subrouter.router,
            dependencies=_WAVE2_SHARED_DEPENDENCIES,
        )


__all__ = ["build_wave2_repository", "get_wave2_repository", "router"]
