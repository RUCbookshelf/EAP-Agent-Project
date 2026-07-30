from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from .schemas import AnalysisUnitRecord, UnitValidationStatus


CLAUSE_DEPS = {"advcl", "ccomp", "xcomp", "acl", "relcl", "csubj"}


class SyntacticUnitSegmenter:
    version = "syntactic-unit-segmenter-v0.8.0"

    def segment_sentences(self, doc) -> list[AnalysisUnitRecord]:
        return [
            AnalysisUnitRecord(
                unit_id="sentence", unit_version="sentence-spacy-v0.8.0",
                start_offset=sent.start_char, end_offset=sent.end_char, source_text=sent.text,
                source_sentence_id=f"S{index:04d}", analyzer_id="spacy",
                parser_evidence={"root": sent.root.text, "root_dependency": sent.root.dep_},
                confidence="medium", validation_status=UnitValidationStatus.VALIDATED_AUTOMATIC,
                rule_ids=["SPACY_SENTENCE_BOUNDARY"],
                limitations=["Sentence boundaries inherit the pinned spaCy model's learner-language limitations."],
            )
            for index, sent in enumerate(doc.sents, 1)
        ]

    def segment_clause_candidates(self, doc) -> list[AnalysisUnitRecord]:
        results: list[AnalysisUnitRecord] = []
        for sentence_index, sent in enumerate(doc.sents, 1):
            for token in sent:
                if token.dep_ not in CLAUSE_DEPS and not (token.dep_ == "ROOT" and token.pos_ in {"VERB", "AUX"}):
                    continue
                subtree = list(token.subtree)
                start = min(item.idx for item in subtree)
                end = max(item.idx + len(item.text) for item in subtree)
                results.append(AnalysisUnitRecord(
                    unit_id="clause_candidate", unit_version="clause-candidate-spacy-v0.8.0",
                    start_offset=start, end_offset=end, source_text=doc.text[start:end],
                    source_sentence_id=f"S{sentence_index:04d}", analyzer_id="spacy",
                    parser_evidence={"head_text": token.text, "dependency": token.dep_, "pos": token.pos_},
                    confidence="low", validation_status=UnitValidationStatus.AUTOMATIC_CANDIDATE,
                    rule_ids=[f"DEPENDENCY_{token.dep_.upper()}"],
                    limitations=["Parser-derived clause candidate; not a validated clause and not eligible for formal CALF ratios."],
                ))
        return results

    def segment_t_unit_candidates(self, doc) -> list[AnalysisUnitRecord]:
        return [
            AnalysisUnitRecord(
                unit_id="t_unit_candidate", unit_version="t-unit-candidate-conservative-v0.8.0",
                start_offset=sent.start_char, end_offset=sent.end_char, source_text=sent.text,
                source_sentence_id=f"S{index:04d}", analyzer_id="spacy",
                parser_evidence={"candidate_basis": "whole sentence envelope", "root": sent.root.text},
                confidence="low", validation_status=UnitValidationStatus.AUTOMATIC_CANDIDATE,
                rule_ids=["SENTENCE_ENVELOPE_T_UNIT_CANDIDATE"],
                limitations=[
                    "Conservative interface candidate only; coordination and embedded structures require human review.",
                    "Not a validated T-unit and not eligible for MLT, C/T, or DC/T calculation.",
                ],
            )
            for index, sent in enumerate(doc.sents, 1)
        ]

    def validate_units(self, units: Iterable[AnalysisUnitRecord], decisions: dict[int, dict]) -> list[AnalysisUnitRecord]:
        validated: list[AnalysisUnitRecord] = []
        for index, unit in enumerate(units):
            decision = decisions.get(index)
            if decision is None:
                validated.append(unit)
                continue
            if decision.get("manual_decision") == "reject":
                validated.append(unit.model_copy(update={
                    "validation_status": UnitValidationStatus.REJECTED,
                    "annotator_id": decision.get("annotator_id"),
                    "annotation_timestamp": decision.get("annotation_timestamp", datetime.now(timezone.utc)),
                    "manual_decision": "reject",
                    "annotation_guideline_version": decision.get("annotation_guideline_version"),
                    "adjudication_status": decision.get("adjudication_status"),
                }))
                continue
            if decision.get("manual_decision") != "accept":
                raise ValueError("Manual validation decision must be accept or reject")
            target = {"clause_candidate": "validated_clause", "t_unit_candidate": "validated_t_unit"}.get(unit.unit_id)
            if target is None:
                raise ValueError("Only clause and T-unit candidates can be promoted by this interface")
            payload = unit.model_dump(mode="python")
            payload.update({
                "unit_id": target, "unit_version": f"{target}-human-v0.8.0",
                "validation_status": UnitValidationStatus.HUMAN_CONFIRMED,
                "annotator_id": decision.get("annotator_id"),
                "annotation_timestamp": decision.get("annotation_timestamp", datetime.now(timezone.utc)),
                "manual_decision": "accept",
                "corrected_start_offset": decision.get("corrected_start_offset"),
                "corrected_end_offset": decision.get("corrected_end_offset"),
                "annotation_guideline_version": decision.get("annotation_guideline_version"),
                "adjudication_status": decision.get("adjudication_status"),
            })
            validated.append(AnalysisUnitRecord.model_validate(payload))
        return validated
