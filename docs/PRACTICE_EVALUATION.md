# Practice Evaluation v0.9

## Evaluation Method

All practice evaluations use a conservative rule-based approach. The `PracticeService.evaluate_attempt()` method:

1. Checks if the attempt status is INVALID_INPUT
2. For `lexical_repetition_local` targets, compares word frequency between source and response
3. Returns completion status and target-action status
4. Attaches limitation notes

## Status Codes

### Completion Status
- `completed`: response meets minimum length requirements
- `incomplete`: response is incomplete
- `invalid`: empty or invalid input

### Target-Action Status
- `candidate_detected`: lexical repetition reduced
- `candidate_not_detected`: no observable change
- `inconclusive`: unable to determine
- `not_applicable`: invalid attempt

## Confidence

All evaluations are marked `medium` confidence with explicit limitation: "Observable evidence is task-specific and does not prove mastery or learning."

## Evaluation Method Enum

- `rule_based` — deterministic string matching (current)
- `llm_assisted_candidate` — reserved for future DeepSeek-assisted evaluation (not active)

## Boundaries

- No mastery language in evaluation output
- No proficiency, score, grade, CEFR, or causal claims
- Evaluations are append-only
