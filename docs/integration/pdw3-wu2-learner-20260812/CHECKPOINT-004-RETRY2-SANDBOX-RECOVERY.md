# PDW3-WU2 LEARNER RETRY-2 - CHECKPOINT 004: Worker Sandbox Recovery (durable)

- run_id: `PDW3-WU2-LEARNER-PRACTICE-REVIEW-TRANSFER-20260812__RETRY-2__20260811T164118Z__8c8d39`
- goal_id: `PDW3-WU2-LEARNER-PRACTICE-REVIEW-TRANSFER-20260812__RETRY-2`
- checkpoint state: A/B/C first attempts blocked by child sandbox helper;
  shell-capable smoke passed under `danger-full-access`; one retry authorized
  and about to be dispatched

## 1. First-attempt result

Workers A, B, and C were launched with the exact required route
`deepseek/deepseek-v4-flash` + `model_reasoning_effort="ultra"` and
`PLANNING_DISABLED=1`, using `-s workspace-write`. Each CLI process returned
exit code 0 after the child agent produced a terminal `BLOCKED` message, but
the child could not execute even read-only shell commands:

```text
windows sandbox: helper_unknown_error: setup refresh had errors
```

The child agents did not write product files or findings files. Their exact
last-message and JSONL/stderr outputs are retained under:

- `workers/A/last-message.txt`, `workers/A/stdout.jsonl`, `workers/A/stderr.log`
- `workers/B/last-message.txt`, `workers/B/stdout.jsonl`, `workers/B/stderr.log`
- `workers/C/last-message.txt`, `workers/C/stdout.jsonl`, `workers/C/stderr.log`

The first stdin-based packet transport error (`No prompt provided via stdin`)
is recorded in CHECKPOINT-003. Direct prompt-argument transport itself is
working; the child sandbox was the remaining failure.

## 2. Recovery probe

A separate no-write shell smoke used the same model/ultra/PLANNING_DISABLED
route with `-s danger-full-access` and direct prompt text. The child ran:

```text
Get-Location
```

and observed:

```text
Path
----
A:\EAP Agent Project\worktrees\learner
```

It then returned exactly `PONG`; CLI exit code was 0. The proxy websocket
returned HTTP 426 and the CLI fell back to HTTP, as in earlier successful
smokes. This demonstrates that the authorized full-access CLI path can execute
read-only shell work in the target worktree. It does not authorize writes
outside the Goal Packet scope.

## 3. Retry rule and next action

The Goal Packet allows at most one retry of a failed bounded slice. A/B/C will
each be retried exactly once with:

- model `deepseek/deepseek-v4-flash`
- reasoning `ultra`
- `PLANNING_DISABLED=1`
- `-s danger-full-access`
- same authorized worktree and same disjoint packet scope
- separate `workers/<letter>/retry1/` evidence output directories

No provider/model/reasoning substitution is being made. If a retry fails,
that slice becomes terminal `BLOCKED` and will not be retried again; the parent
will preserve siblings and return an exact operational handoff.

Retry launch sessions currently active:

| Worker | Session ID | State at checkpoint update |
| --- | --- | --- |
| A | `67614` | RUNNING |
| B | `7417` | RUNNING |
| C | `44393` | RUNNING |

## 4. Scope/resource status

No product source/test file, Program Control file, other worktree, migration,
Git ref, commit, push, PR, merge, promotion, or raw SWECCL path was touched by
the blocked attempts or recovery probe. Existing five untracked LEARNER paths
remain preserved; only authorized RETRY-2 checkpoint/packet/dispatch evidence
has been added.
