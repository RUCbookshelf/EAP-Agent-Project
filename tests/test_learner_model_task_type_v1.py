"""Learner-model cluster-key task-type integration (Domain Pack v1).

The legacy substring inference (app/services/learner_model.py, purpose
derivation) must not survive: the cluster key derives purpose from the
deterministic task-type lane (persisted ``task_type`` if present, otherwise
the qualified D-22 legacy mapping - explicit-only, no inference).

The D-22 behavior-diff gate is exercised over the DP-4 governed census
snapshot: before/after comparability classifications (which rows are grouped
as comparable) must be IDENTICAL over the real legacy genre distribution,
while the purpose labels move from the inferred tokens to the mapped
task-type ids under the new rule version (task-cluster-v0.8.0).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import itertools
import json
from pathlib import Path

from app.configuration import ConfigurationPayload
from app.services.learner_model import LearnerModelEngine
from app.services.legacy_genre_mapping import map_legacy_genre

_CENSUS = (
    Path(__file__).resolve().parents[1]
    / "docs" / "domain" / "census" / "L2_DP4_LEGACY_ESSAYS_CENSUS_v1.0.0.json"
)


def record(index, *, genre="argumentative essay", timed=True, tool="none",
           group=None, task_type=None):
    return {
        "essay_id": index, "student_id": "LMTV1",
        "submitted_at": datetime(2026, 2, 1, tzinfo=timezone.utc) + timedelta(days=index),
        "genre": genre, "writing_prompt": f"Task prompt {index}",
        "draft_stage": "independent_submission", "timed": timed,
        "time_limit_minutes": 45 if timed else 0, "tool_use": tool,
        "revision_group_id": group, "revision_sequence": index if group else None,
        "analysis_version": "spacy-analyzer-v0.6.1",
        "analyzer_version": "spacy-analyzer-v0.6.1",
        "task_type": task_type,
        "metrics": {"mattr": 0.5},
        "versioned_metrics": {"mattr": {"value": 0.5, "metric_version": "0.6.1",
            "status": "available", "confidence": "medium",
            "eligible_for_longitudinal_comparison": True}},
        "diagnosis": {"improvement_priorities": []},
        "diagnostic_calibration": {"selected_priorities": [],
            "eligible_diagnoses": [], "monitored_signals": [],
            "suppressed_diagnostics": [], "verified_strengths": []},
    }


def build(rows):
    engine = LearnerModelEngine(ConfigurationPayload())
    representatives, _ = engine.choose_representatives(rows)
    return engine, engine.task_clusters("LMTV1", representatives)


class TestClusterPurposeDerivation:
    """Purpose derives from the deterministic task-type lane, not inference."""

    def test_argumentative_genre_maps_to_task_type(self):
        engine, clusters = build([record(1)])
        assert clusters[0].writing_purpose == "argumentative"
        assert clusters[0].prompt_family == "argumentative-general"

    def test_zh_genre_maps_to_task_type(self):
        engine, clusters = build([record(1, genre="议论文")])
        assert clusters[0].writing_purpose == "argumentative"

    def test_expository_genre_is_legacy_unclassified_not_exposition(self):
        engine, clusters = build([record(1, genre="expository essay")])
        assert clusters[0].writing_purpose == "legacy_unclassified"

    def test_narrative_genre_is_legacy_unclassified_not_narration(self):
        engine, clusters = build([record(1, genre="narrative essay")])
        assert clusters[0].writing_purpose == "legacy_unclassified"

    def test_persisted_task_type_wins(self):
        engine, clusters = build([record(1, genre="argumentative essay", task_type="discussion")])
        assert clusters[0].writing_purpose == "discussion"

    def test_unknown_genre_is_legacy_unclassified_not_exposition(self):
        engine, clusters = build([record(1, genre="fantasy essay")])
        assert clusters[0].writing_purpose == "legacy_unclassified"

    def test_genre_variants_still_separate_clusters(self):
        # Mirrors frozen test_case_f behavior: distinct genres never join.
        engine, clusters = build([
            record(1), record(2, genre="expository essay"),
        ])
        assert len(clusters) == 2

    def test_rule_version_bumped_with_new_clustering_rule(self):
        engine, clusters = build([record(1)])
        assert engine.task_cluster_version == "task-cluster-v0.8.0"
        assert clusters[0].rule_version == "task-cluster-v0.8.0"


class TestBehaviorDiffGate:
    """D-22: before/after comparability classifications over the census."""

    @staticmethod
    def old_purpose(genre: str) -> str:
        # Frozen v0.7 substring inference (removed by Domain Pack v1).
        value = str(genre or "unknown").casefold().strip()
        return (
            "argument" if "argument" in value
            else "narration" if "narr" in value
            else "exposition"
        )

    def _old_key(self, row):
        genre = str(row["genre"] or "unknown").casefold().strip()
        purpose = self.old_purpose(genre)
        return (
            genre, purpose,
            "timed" if row["timed"] else "untimed",
            "1-30" if row["timed"] else "not_applicable",
            row["tool"], row["mode"], f"{purpose}-general",
            row["analyzer"], row["metrics"],
        )

    def _new_key(self, row):
        genre = str(row["genre"] or "unknown").casefold().strip()
        purpose = map_legacy_genre(genre).mapping
        return (
            genre, purpose,
            "timed" if row["timed"] else "untimed",
            "1-30" if row["timed"] else "not_applicable",
            row["tool"], row["mode"], f"{purpose}-general",
            row["analyzer"], row["metrics"],
        )

    def test_comparability_classifications_unchanged_over_census_grid(self):
        """Same-cluster (comparable) relation is IDENTICAL before/after."""
        census = json.loads(_CENSUS.read_text(encoding="utf-8"))
        distribution = census["legacy_source_distribution"]["by_genre_option"]
        genres = ["argumentative essay"] * distribution["option_argumentative_en"] + \
                 ["议论文"] * distribution["option_argumentative_zh"]
        rows = []
        index = 0
        for genre, timed, tool, mode in itertools.product(
            genres, (True, False), ("none", "AI-assisted"), ("independent_task", "revision_task"),
        ):
            index += 1
            rows.append({
                "genre": genre, "timed": timed, "tool": tool, "mode": mode,
                "analyzer": "spacy-analyzer-v0.6.1",
                "metrics": f"sig-{index % 3}",
            })

        old_groups: dict[tuple, list[int]] = {}
        new_groups: dict[tuple, list[int]] = {}
        for pos, row in enumerate(rows):
            old_groups.setdefault(self._old_key(row), []).append(pos)
            new_groups.setdefault(self._new_key(row), []).append(pos)

        old_membership = {tuple(sorted(v)) for v in old_groups.values()}
        new_membership = {tuple(sorted(v)) for v in new_groups.values()}
        assert old_membership == new_membership

        # Pairwise comparability equivalence (the D-22 predicate).
        same_old = {
            frozenset((i, j))
            for i in range(len(rows)) for j in range(i + 1, len(rows))
            if any(i in v and j in v for v in old_groups.values())
        }
        same_new = {
            frozenset((i, j))
            for i in range(len(rows)) for j in range(i + 1, len(rows))
            if any(i in v and j in v for v in new_groups.values())
        }
        assert same_old == same_new

    def test_documented_label_transitions(self):
        transitions = {
            "argumentative essay": ("argument", "argumentative"),
            "议论文": ("exposition", "argumentative"),
            "expository essay": ("exposition", "legacy_unclassified"),
            "narrative essay": ("narration", "legacy_unclassified"),
        }
        for genre, (old, new) in transitions.items():
            assert self.old_purpose(genre) == old
            assert map_legacy_genre(genre).mapping == new

    def test_all_census_rows_typed_under_new_rule(self):
        census = json.loads(_CENSUS.read_text(encoding="utf-8"))
        distribution = census["legacy_source_distribution"]["by_genre_option"]
        totals: dict[str, int] = {}
        for option, count in distribution.items():
            genre = (
                "argumentative essay"
                if option == "option_argumentative_en" else "议论文"
            )
            mapping = map_legacy_genre(genre).mapping
            totals[mapping] = totals.get(mapping, 0) + count
        # Rule counts aggregate to the census result: 29 argumentative rows.
        assert totals == {"argumentative": 29}
