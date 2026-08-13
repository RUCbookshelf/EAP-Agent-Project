# RETRY-2 Checkpoint 010 — V1 Independent Verification

- Goal/run: `PDW3-WU2-LEARNER-PRACTICE-REVIEW-TRANSFER-20260812__RETRY-2__20260811T164118Z__8c8d39`
- Verifier: `V1`
- Dispatch: `codex.cmd exec --json`; model `deepseek/deepseek-v4-flash`; reasoning effort `ultra`; `PLANNING_DISABLED=1`; `-s read-only`; worktree `A:\EAP Agent Project\worktrees\learner`
- Parent shell session: `6059`
- Terminal state: returned `CONCERNS`; exit code `0`
- Evidence: `workers/V1/last-message.txt`, `workers/V1/stdout.jsonl`, `workers/V1/stderr.log`

## Independent findings

- PASS static scope: branch `dept/feedback-learner`, HEAD
  `7a9e4b470c41c0453a3795233f1bdd5c483d80ae`, four additive tracked files,
  five pre-existing untracked paths present, four available WU0 fingerprints
  byte-identical, no `app/review`, no migration/database edits, and no other
  worktree changes.
- PASS static semantics: practice/review and authentic-application channels
  remain separate; three rating channels and scheduler/rating-rule provenance
  remain separate; acknowledgement is L0/descriptive with consent,
  provenance/version, source-kind, and fail-closed gates; no duplicate route
  pairs or second database authority.
- CONFIRMED blocker 1: the two Worker B projections are service-level only;
  no `practice-history` or `authentic-application` API route exists because
  `app/api/routers/journey.py` was outside D's write packet.
- CONFIRMED blocker 2: the unmodified v0.9.5-B exact route pin lacks the two
  required acknowledgement pairs; the unmodified v0.9.5-D contract still
  pins 81 endpoints while the baseline was already 100 and final runtime is
  102.

## Verification limitation

The read-only sandbox had no writable temporary directory, so pytest could
not start (`FileNotFoundError: No usable temporary directory`). A nested
fallback smoke attempt was not usable because that child fell back to
`api.openai.com` and sockets were denied (`os error 10013`). V1 therefore
returned `CONCERNS`, not `FAIL`; the parent-owned executable regression is the
test evidence for this handoff:

- WU2 focused: `121 passed, 2 warnings`.
- Journey/Wave-2/Learner: `396 passed, 2 warnings`.
- Practice/narrowing: `251 passed, 2 warnings`.
- Composition/router pins: `28 passed, 2 failed`, exactly the two recorded
  unowned contract-pin findings.

No product repair, evidence-file mutation by V1, Git mutation, Program
Control write, commit, push, PR, merge, promotion, reset, clean, restore, or
rebase occurred. The next action is the canonical AMBER learner handoff;
promotion remains false.
