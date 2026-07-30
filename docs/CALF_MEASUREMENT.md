# CALF Measurement Foundation v0.8

v0.8 adds an auditable foundation for Complexity, Accuracy, Lexical Complexity, and Product Fluency research measures. It is not a CALF score, writing-quality score, proficiency/ability estimate, CEFR mapping, or educationally validated instrument.

Every measure is bound to a construct/subconstruct, exact metric version, analysis-unit version, formula, parameters, minimum input, automation level, lifecycle, eligibility flags, references, intermediate values, and limitations. The registry distinguishes `research_metric`, `descriptive_proxy`, `automatic_candidate`, `manual_annotation_required`, and `unavailable`.

Implemented research measures are TTR 2.0.0, MATTR 0.6.1, MTLD 0.8.0, HD-D 0.8.0, and lexical density 0.6.1. Writing output rate 0.8.0 is an implemented descriptive proxy only when actual duration is available. Syntax outputs remain parser candidates. Accuracy requires confirmed annotations and a validated denominator; lexical sophistication remains unavailable.

CALF-only measures are research-audit data by default. They do not create diagnoses, priorities, exercises, or student totals. Longitudinal series require exact metric version, analysis-unit version, Analyzer compatibility, and task-condition grouping.
