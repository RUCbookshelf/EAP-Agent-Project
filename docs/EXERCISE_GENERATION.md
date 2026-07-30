# Exercise Generation v0.9

## Current Implementation

All exercise instances are generated deterministically from the `ExerciseSpecification` registry. Three exercise types are defined:

- **Guided Sentence Rewrite** — for `lexical_repetition_local`, `connective_overuse`, `long_sentence`
- **Constrained Micro Revision** — for `lexical_repetition_local`, `connective_overuse`, `vague_organization`
- **Target Feature Identification** — for `lexical_repetition_local`, `connective_overuse`, `long_sentence`

## Deterministic Template

The `PracticeService.generate_exercise()` method:
1. Looks up the target code in the exercise specification registry
2. Selects the first matching exercise type
3. Returns a template with localized instructions, constraints, source text (truncated to 500 chars), and limitation notes

## DeepSeek-Assisted Generation

DeepSeek-assisted exercise generation is disabled by default (`exercise_generation_provider: deterministic_template`). The API and configuration support enabling it, but no prompts or DeepSeek integration is active in this version.

## Unsupported Targets

If a target code has no matching exercise specification, the service returns `practice_not_available` status. No generic exercise is generated for unsupported targets.

## Idempotency

Repeated calls to `generate_exercise` for the same target produce identical exercise types and instructions. Exercise Instance IDs are assigned at persistence time, not generation time.
