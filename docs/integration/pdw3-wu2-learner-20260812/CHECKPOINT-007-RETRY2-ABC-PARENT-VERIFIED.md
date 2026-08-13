# PDW3-WU2 LEARNER RETRY-2 - CHECKPOINT 007: A/B/C Parent Verification (durable)

- run_id: `PDW3-WU2-LEARNER-PRACTICE-REVIEW-TRANSFER-20260812__RETRY-2__20260811T164118Z__8c8d39`
- goal_id: `PDW3-WU2-LEARNER-PRACTICE-REVIEW-TRANSFER-20260812__RETRY-2`
- worktree: `A:\EAP Agent Project\worktrees\learner`
- branch: `dept/feedback-learner`
- starting_sha: `7a9e4b470c41c0453a3795233f1bdd5c483d80ae`
- state: A/B/C terminal DONE; parent focused gate GREEN; D dispatched next;
  V1 waits for D and final regression

## Worker results accepted

| Worker | Session/exit | Findings | Worker verification |
| --- | --- | --- | --- |
| A | `67614` / exit 0 | `workers/A/findings.md` | 40 focused; 250 learner; repeated focused reruns stable; structural CORE bridge; no copied `app/review`, no migration/adapter/database |
| B | `7417` / exit 0 | `workers/B/findings.md` | 18 focused; 439 Journey/Wave-2/learner regression; 249 broader practice/composition/service-narrowing sweep; 0 failed; additive Journey methods preserve exact `get_journey()`/9-port pins |
| C | `44393` / exit 0 | `workers/C/findings.md` | 51 focused; 250 learner; 265 adjacent shared/Wave-2; consent/provenance/version/ownership/semantic/duplicate/conflict fail-closed and no-write paths |

All three used `deepseek/deepseek-v4-flash`, reasoning `ultra`, and
`PLANNING_DISABLED=1` on the one allowed `danger-full-access` retry. Their
first workspace-write attempts remain preserved as exact terminal sandbox
blockers; no additional retry is authorized.

## Parent-side quiet-worktree gate

Command:

```text
$env:PYTHONDONTWRITEBYTECODE='1'
.\\.venv\\Scripts\\python.exe -m pytest tests/learner/test_wu2_practice_review_evidence.py tests/learner/test_wu2_acknowledgement.py tests/learner/test_wu2_journey_history_transfer.py -q --no-header -p no:cacheprovider
```

Observed: `109 passed, 1 warning in 2.98s` (exit 0). The warning is the
existing Starlette/httpx deprecation warning.

Scope audit observed:

- HEAD remains `7a9e4b470c41c0453a3795233f1bdd5c483d80ae`.
- Branch remains `dept/feedback-learner`.
- Tracked diff is only `app/journey/service.py` (additive).
- Intended new files are the A/B/C source/tests/findings plus evidence.
- `app/review` does not exist in LEARNER; migrations, `app/api/main.py`, and
  `app/api/deps.py` are unmodified.
- Five pre-existing untracked evidence/test paths remain present and
  preserved; no other worktree or Program Control file was written.

## Next action

Dispatch Worker D with the same exact DeepSeek/ultra/PLANNING_DISABLED route,
using only `app/api/main.py`, `app/api/deps.py`, its focused composition test,
and its findings file. D must wire the acknowledged service, A bridge, and B
Journey projection methods through the existing single composition root. After
D exits, run parent focused/API/Wave-2 regression and dispatch fresh V1
read-only verification. No promotion or merge is authorized.

