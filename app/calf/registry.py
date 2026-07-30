from __future__ import annotations

from collections.abc import Iterable

from .schemas import (
    AnalysisUnitDefinition, AutomationLevel, CalfConstruct, ConstructStatus,
    MeasurementSpecification, MeasurementStatus, MetricLifecycle, UnitValidationStatus,
)


class CalfRegistry:
    def __init__(self, constructs: Iterable[CalfConstruct] = (),
                 specifications: Iterable[MeasurementSpecification] = (),
                 units: Iterable[AnalysisUnitDefinition] = ()) -> None:
        self._constructs: dict[str, CalfConstruct] = {}
        self._specifications: dict[tuple[str, str], MeasurementSpecification] = {}
        self._units: dict[tuple[str, str], AnalysisUnitDefinition] = {}
        for item in constructs:
            self.register_construct(item)
        for item in units:
            self.register_unit(item)
        for item in specifications:
            self.register_specification(item)

    def register_construct(self, item: CalfConstruct) -> None:
        if item.construct_id in self._constructs:
            raise ValueError(f"CALF construct already registered: {item.construct_id}")
        self._constructs[item.construct_id] = item

    def register_unit(self, item: AnalysisUnitDefinition) -> None:
        key = (item.unit_id, item.unit_version)
        if key in self._units:
            raise ValueError(f"Analysis unit already registered: {key}")
        self._units[key] = item

    def register_specification(self, item: MeasurementSpecification) -> None:
        key = (item.metric_id, item.metric_version)
        if key in self._specifications:
            raise ValueError(f"CALF metric specification already registered: {key}")
        if item.construct_id not in self._constructs:
            raise ValueError(f"Unknown construct: {item.construct_id}")
        if not any(unit_id == item.analysis_unit for unit_id, _ in self._units):
            raise ValueError(f"Unknown analysis unit: {item.analysis_unit}")
        self._specifications[key] = item

    def list_constructs(self) -> list[CalfConstruct]:
        return [self._constructs[key] for key in sorted(self._constructs)]

    def list_units(self) -> list[AnalysisUnitDefinition]:
        return [self._units[key] for key in sorted(self._units)]

    def list_specifications(self, *, construct_id: str | None = None,
                            subconstruct_id: str | None = None,
                            measurement_status: str | None = None,
                            automation_level: str | None = None,
                            student_feedback_eligible: bool | None = None,
                            diagnosis_eligible: bool | None = None,
                            longitudinal_eligible: bool | None = None,
                            analyzer_requirement: str | None = None,
                            resource_requirement: str | None = None,
                            manual_annotation_required: bool | None = None) -> list[MeasurementSpecification]:
        items = list(self._specifications.values())
        filters = {
            "construct_id": construct_id, "subconstruct_id": subconstruct_id,
            "measurement_status": measurement_status, "automation_level": automation_level,
            "eligible_for_student_feedback": student_feedback_eligible,
            "eligible_for_diagnosis": diagnosis_eligible,
            "eligible_for_longitudinal_tracking": longitudinal_eligible,
            "analyzer_requirement": analyzer_requirement,
            "manual_annotation_required": manual_annotation_required,
        }
        for field, expected in filters.items():
            if expected is not None:
                items = [item for item in items if getattr(item, field) == expected]
        if resource_requirement is not None:
            items = [item for item in items if resource_requirement in item.resource_requirements]
        return sorted(items, key=lambda item: (item.construct_id, item.subconstruct_id, item.metric_id, item.metric_version))

    def get_specification(self, metric_id: str, metric_version: str | None = None) -> MeasurementSpecification:
        items = [item for (mid, _), item in self._specifications.items() if mid == metric_id]
        if metric_version is not None:
            items = [item for item in items if item.metric_version == metric_version]
        if not items:
            raise ValueError(f"Unknown CALF metric: {metric_id}")
        if metric_version is None and len(items) > 1:
            items = sorted(items, key=lambda item: item.metric_version)
        return items[-1]


def _constructs() -> list[CalfConstruct]:
    boundary = "Observed text values are research evidence, not writing quality, ability, mastery, CEFR, or a score."
    return [
        CalfConstruct(
            construct_id="lexical_complexity", display_name="Lexical Complexity",
            definition="A multidimensional description of lexical diversity, density, and sophistication in a text.",
            subconstructs=["lexical_diversity", "lexical_density", "lexical_sophistication"],
            status=ConstructStatus.VALIDATION_PENDING, interpretation_boundary=boundary,
            reference_ids=["REF-CALF-001", "REF-LD-001"],
            limitations=["No v0.8 measure has been validated for the target Chinese university learner population."],
        ),
        CalfConstruct(
            construct_id="syntactic_complexity", display_name="Syntactic Complexity",
            definition="Structural properties of syntactic units, represented in v0.8 only by candidate foundations.",
            subconstructs=["clausal", "phrasal", "coordination", "dependency_candidates"],
            status=ConstructStatus.VALIDATION_PENDING, interpretation_boundary=boundary,
            reference_ids=["REF-SYNTAX-001"],
            limitations=["Parser candidates are not validated clauses, T-units, or formal syntactic-complexity measures."],
        ),
        CalfConstruct(
            construct_id="accuracy", display_name="Accuracy",
            definition="Error-related observations calculated only from eligible validated annotations.",
            subconstructs=["grammatical_accuracy", "lexical_accuracy"],
            status=ConstructStatus.UNAVAILABLE, interpretation_boundary=boundary,
            reference_ids=["REF-ACCURACY-001"],
            limitations=["No automatic accuracy measure is implemented in v0.8."],
        ),
        CalfConstruct(
            construct_id="product_fluency", display_name="Product Fluency",
            definition="Descriptive production-output measures tied to actual writing duration.",
            subconstructs=["writing_output_rate"], status=ConstructStatus.PROTOTYPE,
            interpretation_boundary=boundary, reference_ids=["REF-FLUENCY-001"],
            limitations=["Output rate is a descriptive proxy and not a standalone fluency-ability measure."],
        ),
    ]


def _units() -> list[AnalysisUnitDefinition]:
    definitions = [
        ("raw_character", "raw-character-v0.8.0", "Raw Character", "preserved source-text character", None, None, UnitValidationStatus.VALIDATED_AUTOMATIC),
        ("normalized_word_token", "normalized-word-token-v0.8.0", "Normalized Word Token", "alphabetic spaCy token plus lowercase surface normalization", "spacy", "raw_character", UnitValidationStatus.VALIDATED_AUTOMATIC),
        ("lemma", "lemma-spacy-v0.8.0", "Lemma", "lowercase spaCy lemma", "spacy", "normalized_word_token", UnitValidationStatus.AUTOMATIC_CANDIDATE),
        ("sentence", "sentence-spacy-v0.8.0", "Sentence", "spaCy sentence boundary", "spacy", "raw_character", UnitValidationStatus.VALIDATED_AUTOMATIC),
        ("paragraph", "paragraph-blank-line-v0.8.0", "Paragraph", "non-empty blank-line-delimited span", None, "raw_character", UnitValidationStatus.VALIDATED_AUTOMATIC),
        ("dependency_node", "dependency-node-spacy-v0.8.0", "Dependency Node", "spaCy dependency parse token", "spacy", "sentence", UnitValidationStatus.AUTOMATIC_CANDIDATE),
        ("noun_chunk_candidate", "noun-chunk-spacy-v0.8.0", "Noun Chunk Candidate", "spaCy noun_chunks", "spacy", "sentence", UnitValidationStatus.AUTOMATIC_CANDIDATE),
        ("clause_candidate", "clause-candidate-spacy-v0.8.0", "Clause Candidate", "conservative dependency candidate", "spacy", "sentence", UnitValidationStatus.AUTOMATIC_CANDIDATE),
        ("t_unit_candidate", "t-unit-candidate-conservative-v0.8.0", "T-unit Candidate", "conservative sentence-envelope candidate", "spacy", "sentence", UnitValidationStatus.AUTOMATIC_CANDIDATE),
        ("validated_clause", "validated-clause-human-v0.8.0", "Validated Clause", "human confirmation under versioned guideline", None, "clause_candidate", UnitValidationStatus.HUMAN_CONFIRMED),
        ("validated_t_unit", "validated-t-unit-human-v0.8.0", "Validated T-unit", "human confirmation under versioned guideline", None, "t_unit_candidate", UnitValidationStatus.HUMAN_CONFIRMED),
        ("error_span_candidate", "error-span-candidate-v0.8.0", "Error Span Candidate", "imported/tool/LLM candidate annotation", None, "raw_character", UnitValidationStatus.AUTOMATIC_CANDIDATE),
        ("validated_error_span", "validated-error-span-human-v0.8.0", "Validated Error Span", "eligible confirmed human/imported annotation", None, "error_span_candidate", UnitValidationStatus.HUMAN_CONFIRMED),
        ("timed_writing_event", "timed-writing-event-v0.8.0", "Timed Writing Event", "recorded actual active-writing duration event", None, None, UnitValidationStatus.NOT_AVAILABLE),
    ]
    return [AnalysisUnitDefinition(
        unit_id=unit_id, unit_version=version, display_name=label, generation_method=method,
        analyzer_requirement=analyzer, parent_unit=parent, default_validation_status=status,
        limitations=["Unit boundaries and validation state must be retained with every derived value."],
    ) for unit_id, version, label, method, analyzer, parent, status in definitions]


def _spec(metric_id: str, metric_version: str, construct_id: str, subconstruct_id: str,
          display_name: str, status: MeasurementStatus, automation: AutomationLevel,
          unit: str, unit_version: str, formula: str, normalization: str,
          minimum: dict, output_unit: str, references: list[str], limitations: list[str],
          *, parameters: dict | None = None, numerator: str | None = None,
          denominator: str | None = None, longitudinal: bool = False,
          analyzer: str | None = None, manual: bool = False,
          lifecycle: MetricLifecycle = MetricLifecycle.ACTIVE_RESEARCH,
          fixtures: list[str] | None = None) -> MeasurementSpecification:
    return MeasurementSpecification(
        metric_id=metric_id, metric_version=metric_version, construct_id=construct_id,
        subconstruct_id=subconstruct_id, display_name=display_name, definition=display_name,
        measurement_status=status, automation_level=automation, lifecycle=lifecycle,
        analysis_unit=unit, analysis_unit_version=unit_version,
        formula_description=formula, numerator_description=numerator,
        denominator_description=denominator, normalization=normalization,
        parameters=parameters or {}, minimum_data_requirements=minimum,
        output_unit=output_unit, eligible_for_longitudinal_tracking=longitudinal,
        analyzer_requirement=analyzer, manual_annotation_required=manual,
        fixture_ids=fixtures or ["CALF-CASE-A-M"], reference_ids=references,
        known_limitations=limitations,
    )


def _specifications() -> list[MeasurementSpecification]:
    lexical_limit = ["Text-length, tokenization, task, and population effects require research review."]
    items = [
        _spec("type_token_ratio", "2.0.0", "lexical_complexity", "lexical_diversity", "Type-token ratio",
              MeasurementStatus.RESEARCH_METRIC, AutomationLevel.DETERMINISTIC,
              "normalized_word_token", "normalized-word-token-v0.8.0", "number of unique normalized tokens / normalized token count",
              "lowercase surface; alphabetic spaCy tokens; punctuation and numbers excluded", {"minimum_tokens": 1}, "ratio",
              ["REF-LD-TTR-001"], lexical_limit, numerator="unique normalized token count", denominator="normalized token count", longitudinal=True, analyzer="spacy"),
        _spec("mattr", "0.6.1", "lexical_complexity", "lexical_diversity", "Moving-average type-token ratio",
              MeasurementStatus.RESEARCH_METRIC, AutomationLevel.DETERMINISTIC,
              "normalized_word_token", "normalized-word-token-v0.8.0", "mean TTR across all overlapping configured-size token windows",
              "lowercase surface; alphabetic spaCy tokens", {"minimum_tokens": "configured window_size"}, "ratio",
              ["REF-LD-MATTR-001"], lexical_limit, parameters={"window_size": 50}, longitudinal=True, analyzer="spacy"),
        _spec("mtld", "0.8.0", "lexical_complexity", "lexical_diversity", "Measure of Textual Lexical Diversity",
              MeasurementStatus.RESEARCH_METRIC, AutomationLevel.DETERMINISTIC,
              "normalized_word_token", "normalized-word-token-v0.8.0", "mean forward/reverse token count divided by complete plus proportional partial factors at the configured TTR threshold",
              "lowercase surface; alphabetic spaCy tokens", {"minimum_tokens": 10}, "index",
              ["REF-LD-MTLD-001", "REF-IMPLEMENTATION-001"], lexical_limit,
              parameters={"factor_threshold": 0.72, "calculate_reverse": True, "partial_factor_method": "proportional"},
              longitudinal=True, analyzer="spacy", fixtures=["CALF-A", "CALF-B", "CALF-C", "CALF-D", "CALF-E"]),
        _spec("hdd", "0.8.0", "lexical_complexity", "lexical_diversity", "Hypergeometric distribution diversity",
              MeasurementStatus.RESEARCH_METRIC, AutomationLevel.DETERMINISTIC,
              "normalized_word_token", "normalized-word-token-v0.8.0", "sum over types of 1-C(N-frequency,n)/C(N,n), divided by n",
              "lowercase surface; alphabetic spaCy tokens", {"minimum_tokens": "configured sample_size"}, "expected_sample_ttr",
              ["REF-LD-HDD-001", "REF-IMPLEMENTATION-001"], lexical_limit,
              parameters={"sample_size": 42, "short_text_policy": "unavailable"}, longitudinal=True, analyzer="spacy",
              fixtures=["CALF-A", "CALF-B", "CALF-C", "CALF-D", "CALF-F"]),
        _spec("lexical_density", "0.6.1", "lexical_complexity", "lexical_density", "Lexical density",
              MeasurementStatus.RESEARCH_METRIC, AutomationLevel.PARSER_DEPENDENT,
              "normalized_word_token", "normalized-word-token-v0.8.0", "NOUN/PROPN/VERB/ADJ/ADV alphabetic token count / alphabetic token count",
              "spaCy POS over alphabetic tokens; AUX excluded; PROPN included", {"minimum_tokens": 1}, "ratio",
              ["REF-LD-DENSITY-001"], ["spaCy POS errors can change numerator membership; density is not lexical level."],
              parameters={"content_pos": ["NOUN", "PROPN", "VERB", "ADJ", "ADV"], "aux_policy": "excluded"},
              numerator="configured content POS token count", denominator="alphabetic token count", longitudinal=True, analyzer="spacy"),
        _spec("lexical_sophistication", "0.8.0", "lexical_complexity", "lexical_sophistication", "Lexical sophistication",
              MeasurementStatus.UNAVAILABLE, AutomationLevel.EXTERNAL_RESOURCE_DEPENDENT,
              "normalized_word_token", "normalized-word-token-v0.8.0", "not defined: no authorized versioned frequency resource",
              "not available", {"authorized_frequency_resource": True}, "unavailable",
              ["REF-LD-SOPHISTICATION-PENDING"], ["No authorized frequency resource, band definition, OOV/proper-noun/multiword policy, or target-corpus calibration is present."],
              lifecycle=MetricLifecycle.PROTOTYPE, fixtures=["CALF-UNAVAILABLE"]),
        _spec("writing_output_rate_wpm", "0.8.0", "product_fluency", "writing_output_rate", "Writing output rate",
              MeasurementStatus.DESCRIPTIVE_PROXY, AutomationLevel.DETERMINISTIC,
              "timed_writing_event", "timed-writing-event-v0.8.0", "normalized word count / actual active-writing minutes",
              "alphabetic token count; actual duration only", {"timed": True, "positive_actual_duration": True, "accepted_timing_quality": True}, "words_per_minute",
              ["REF-FLUENCY-001"], ["A production-condition proxy, not a standalone fluency or ability score."],
              numerator="normalized word count", denominator="active_writing_duration_seconds / 60", longitudinal=True,
              fixtures=["CALF-G", "CALF-H"]),
    ]
    syntax_candidates = [
        ("mean_dependency_tree_depth", "dependency_node", "dependency-node-spacy-v0.8.0"),
        ("mean_noun_phrase_length", "noun_chunk_candidate", "noun-chunk-spacy-v0.8.0"),
        ("clause_like_dependency_candidates", "clause_candidate", "clause-candidate-spacy-v0.8.0"),
        ("coordinator_token_count", "dependency_node", "dependency-node-spacy-v0.8.0"),
        ("conjunct_dependency_count", "dependency_node", "dependency-node-spacy-v0.8.0"),
        ("coordinated_structure_candidates", "dependency_node", "dependency-node-spacy-v0.8.0"),
        ("finite_verb_candidates", "dependency_node", "dependency-node-spacy-v0.8.0"),
        ("long_sentence_candidates", "sentence", "sentence-spacy-v0.8.0"),
        ("clause_candidate_count", "clause_candidate", "clause-candidate-spacy-v0.8.0"),
        ("t_unit_candidate_count", "t_unit_candidate", "t-unit-candidate-conservative-v0.8.0"),
    ]
    for metric_id, unit, unit_version in syntax_candidates:
        items.append(_spec(
            metric_id, "0.8.0", "syntactic_complexity", "parser_candidate", metric_id.replace("_", " ").title(),
            MeasurementStatus.AUTOMATIC_CANDIDATE, AutomationLevel.PARSER_DEPENDENT,
            unit, unit_version, "parser/rule-derived candidate calculation", "pinned spaCy output",
            {"validated_units_required_for_formal_measure": True}, "candidate",
            ["REF-SYNTAX-001"], ["Research-audit candidate only; not a validated syntactic-complexity measure."],
            analyzer="spacy", lifecycle=MetricLifecycle.PROTOTYPE, fixtures=["CALF-I"],
        ))
    for metric_id in (
        "errors_per_100_words", "error_free_clause_ratio", "error_free_t_unit_ratio",
        "grammatical_error_density", "lexical_error_density",
    ):
        unit = "validated_clause" if "clause" in metric_id else "validated_t_unit" if "t_unit" in metric_id else "validated_error_span"
        items.append(_spec(
            metric_id, "0.8.0", "accuracy", "validated_error_annotation", metric_id.replace("_", " ").title(),
            MeasurementStatus.MANUAL_ANNOTATION_REQUIRED, AutomationLevel.MANUAL,
            unit, next(item.unit_version for item in _units() if item.unit_id == unit),
            "not calculated without eligible confirmed human/imported annotations and a validated denominator",
            "confirmed human/imported annotations only", {"eligible_confirmed_annotations": 1}, "unavailable_or_ratio",
            ["REF-ACCURACY-001"], ["v0.8 provides the annotation foundation but not an automatic Accuracy measure."],
            manual=True, lifecycle=MetricLifecycle.PROTOTYPE, fixtures=["CALF-J", "CALF-K"],
        ))
    return items


def default_calf_registry() -> CalfRegistry:
    return CalfRegistry(_constructs(), _specifications(), _units())
