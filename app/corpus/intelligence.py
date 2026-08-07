"""WU7 — Corpus Intelligence query boundary (read-only, internal).

Stage 6 will consume distributions through this boundary without inspecting
corpus files or preparation CSVs. Learner-facing corpus exposure stays
disabled: every result carries learner_exposure="research_only".
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.corpus.distributions import ReferenceDistribution
from app.corpus.errors import CorpusInvalidRequestError, CorpusUnavailableError
from app.corpus.features import FEATURE_DEFINITIONS, FEATURE_SET_VERSION
from app.corpus.groups import ReferenceGroup, ReferenceGroupIndex
from app.corpus.resource import CorpusResourceDescriptor, get_corpus_resource

REPO_ROOT = Path(r"A:\EAP Agent Project\writing-feedback-mvp")
INTELLIGENCE_DATA = REPO_ROOT / "docs" / "corpus-intelligence" / "l2" / "data"


@dataclass(frozen=True)
class DistributionQueryResult:
    corpus_package_id: str
    manifest_hash: str
    requested_reference_group: str
    resolved_reference_group: str
    fallback_disclosure: str | None
    feature_id: str
    feature_set_version: str
    n_effective: int
    n_raw: int
    distribution: ReferenceDistribution | None
    availability: str
    limitations: tuple[str, ...]
    learner_exposure: str = "research_only"


class CorpusIntelligence:
    """Read-only facade over registered corpus resources and artifacts."""

    def __init__(
        self,
        *,
        resource: CorpusResourceDescriptor | None = None,
        index: ReferenceGroupIndex | None = None,
        distributions: dict[tuple[str, str], ReferenceDistribution] | None = None,
        data_dir: Path = INTELLIGENCE_DATA,
    ) -> None:
        self.resource = resource if resource is not None else get_corpus_resource()
        self.index = index if index is not None else ReferenceGroupIndex()
        self.distributions = distributions if distributions is not None else self._load_distributions(data_dir)
        self.data_dir = data_dir

    @staticmethod
    def _load_distributions(data_dir: Path) -> dict[tuple[str, str], ReferenceDistribution]:
        path = data_dir / "reference_distributions.jsonl"
        result: dict[tuple[str, str], ReferenceDistribution] = {}
        if not path.is_file():
            return result
        with open(path, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                item = json.loads(line)
                result[(item["reference_group_id"], item["feature_id"])] = ReferenceDistribution(**item)
        return result

    def get_corpus_version(self) -> dict:
        return {
            **self.resource.provenance,
            "readiness_dir": str(self.resource.readiness_dir),
            "license_status": self.resource.license_status,
            "known_limitations": list(self.resource.known_limitations),
        }

    def get_resource(self) -> CorpusResourceDescriptor:
        return self.resource

    def get_feature_definition(self, feature_id: str) -> dict:
        definition = FEATURE_DEFINITIONS.get(feature_id)
        if definition is None:
            raise CorpusInvalidRequestError(f"unknown feature: {feature_id}")
        return {
            **definition.__dict__,
            "feature_set_version": FEATURE_SET_VERSION,
        }

    def get_reference_group(self, group_id: str) -> ReferenceGroup:
        return self.index.get(group_id)

    def resolve_reference_group(
        self, *, prompt_id: str | None = None, timed_status: str | None = None,
        genre: str | None = None,
    ) -> tuple[ReferenceGroup, str | None]:
        return self.index.resolve(prompt_id=prompt_id, timed_status=timed_status, genre=genre)

    def get_distribution_availability(self, group_id: str, feature_id: str) -> dict:
        key = (group_id, feature_id)
        if key not in self.distributions:
            return {"group_id": group_id, "feature_id": feature_id, "availability": "unavailable",
                    "reason": "distribution artifact missing"}
        dist = self.distributions[key]
        return {"group_id": group_id, "feature_id": feature_id, "availability": dist.availability,
                "reason": "; ".join(dist.validity_flags) or "none"}

    def get_feature_distribution(
        self,
        *,
        reference_group_id: str | None = None,
        feature_id: str,
        prompt_id: str | None = None,
        timed_status: str | None = None,
        genre: str | None = None,
    ) -> DistributionQueryResult:
        if feature_id not in FEATURE_DEFINITIONS:
            raise CorpusInvalidRequestError(f"unknown feature: {feature_id}")
        if reference_group_id is not None:
            group = self.index.get(reference_group_id)
            resolved_id = group.reference_group_id
            requested_id = reference_group_id
            fallback = None
        else:
            requested_id = f"prompt={prompt_id} timed={timed_status} genre={genre}"
            group, fallback = self.index.resolve(
                prompt_id=prompt_id, timed_status=timed_status, genre=genre
            )
            resolved_id = group.reference_group_id
        key = (resolved_id, feature_id)
        dist = self.distributions.get(key)
        if dist is None or dist.availability == "unavailable":
            raise CorpusUnavailableError(
                f"distribution unavailable for {resolved_id} x {feature_id}"
            )
        return DistributionQueryResult(
            corpus_package_id=self.resource.corpus_package_id,
            manifest_hash=self.resource.manifest_hash,
            requested_reference_group=requested_id,
            resolved_reference_group=resolved_id,
            fallback_disclosure=fallback,
            feature_id=feature_id,
            feature_set_version=dist.feature_set_version,
            n_effective=dist.n_effective,
            n_raw=dist.n_raw,
            distribution=dist,
            availability=dist.availability,
            limitations=group.limitations + tuple(dist.validity_flags),
        )


def create_intelligence(data_dir: Path = INTELLIGENCE_DATA) -> CorpusIntelligence:
    return CorpusIntelligence(data_dir=data_dir)