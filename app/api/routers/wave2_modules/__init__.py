"""Wave-2 sub-router modules package (Goal PDW2-A-CORE-PERSISTENCE).

Later department Goals add the sub-router modules here:

- learner_api (LEARNER Goal PDW2-B-LEARNER-MODEL)
- revision_api (L2 Goal PDW2-C-L2-REVISION-SCAFFOLD)
- personalized_api (L2 Goal PDW2-C-L2-REVISION-SCAFFOLD)

Each module must expose a module-level ``router`` (fastapi.APIRouter). The
``app.api.routers.wave2`` assembly statically imports them with graceful
ImportError tolerance, so this package deliberately performs no imports of
its own until those modules exist.
"""

