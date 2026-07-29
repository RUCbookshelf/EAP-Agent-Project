from __future__ import annotations

from .schemas import RevisionComparabilityResult


class RevisionComparabilityService:
    version = "revision-comparability-v0.5.0"

    def compare(self, source: dict, target: dict, *, full_text_similarity: float) -> RevisionComparabilityResult:
        matched: list[str] = []
        mismatched: list[str] = []
        reasons: list[str] = []
        if source.get("student_id") != target.get("student_id"):
            return RevisionComparabilityResult(
                status="not_comparable", matched_conditions=[], mismatched_conditions=["student_id"],
                reasons=["Cross-student revision comparison is forbidden."], confidence="insufficient",
            )
        if target.get("revision_of_submission_id") != source.get("essay_id"):
            return RevisionComparabilityResult(
                status="not_comparable", matched_conditions=["student_id"], mismatched_conditions=["explicit_revision_relationship"],
                reasons=["No explicit direct revision relationship is recorded."], confidence="insufficient",
            )
        matched += ["student_id", "explicit_revision_relationship"]
        for field in ("writing_prompt", "genre", "timed", "time_limit_minutes", "tool_use"):
            if source.get(field) == target.get(field):
                matched.append(field)
            else:
                mismatched.append(field)
                reasons.append(f"{field} differs between linked drafts.")
        if not str(source.get("essay_text", "")).strip() or not str(target.get("essay_text", "")).strip():
            return RevisionComparabilityResult(
                status="insufficient_information", matched_conditions=matched,
                mismatched_conditions=[*mismatched, "valid_text"], reasons=[*reasons, "A linked draft is blank."],
                confidence="insufficient",
            )
        if full_text_similarity < 0.35:
            return RevisionComparabilityResult(
                status="major_rewrite", matched_conditions=matched, mismatched_conditions=mismatched,
                reasons=[*reasons, f"Whole-text similarity is {full_text_similarity:.2f}, below the prototype major-rewrite boundary."],
                confidence="low",
            )
        status = "direct_revision" if not mismatched else "partial_revision"
        reasons = reasons or ["The explicit link and recorded task conditions support direct revision comparison."]
        return RevisionComparabilityResult(
            status=status, matched_conditions=matched, mismatched_conditions=mismatched,
            reasons=reasons, confidence="medium" if status == "direct_revision" else "low",
        )

