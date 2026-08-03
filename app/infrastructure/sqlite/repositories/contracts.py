from __future__ import annotations

from typing import Any, Protocol


class AnalysisRunReader(Protocol):
    def get_latest_analysis_run(self, essay_id: int) -> dict[str, Any] | None: ...
