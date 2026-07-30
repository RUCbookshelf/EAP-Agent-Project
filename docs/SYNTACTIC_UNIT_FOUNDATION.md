# Syntactic Unit Foundation v0.8

`SyntacticUnitSegmenter` emits sentences, dependency-based clause candidates, and conservative sentence-envelope T-unit candidates with offsets, rule IDs, parser evidence, relationships, confidence, and limitations. These records are research-audit candidates only.

v0.8 does not calculate formal MLT, C/T, DC/T, or any validated syntactic-complexity score. Existing tree-depth, noun-phrase, coordination, finite-verb, clause-like, clause-count, and T-unit-count outputs are registered as `automatic_candidate`; all diagnosis, revision-priority, targeted-practice, and longitudinal flags are false. Human promotion produces a new validated-unit identity rather than silently changing a candidate's meaning.
