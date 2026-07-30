# Analysis Units v0.8

The registry defines 14 versioned units: raw character, normalized word token, lemma, sentence, paragraph, dependency node, noun-chunk candidate, clause candidate, T-unit candidate, validated clause, validated T-unit, error-span candidate, validated error span, and timed-writing event.

Persisted unit records retain offsets, source text/sentence, parent/children, rule IDs, parser evidence, Analyzer, confidence, validation state, limitations, and reserved human-review/adjudication fields. Automatic candidates cannot be renamed or treated as validated units without an explicit human confirmation containing annotator, timestamp, decision, guideline version, and corrected offsets where needed.
