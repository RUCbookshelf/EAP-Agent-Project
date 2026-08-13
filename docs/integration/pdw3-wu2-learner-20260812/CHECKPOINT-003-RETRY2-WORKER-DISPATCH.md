# PDW3-WU2 LEARNER RETRY-2 - CHECKPOINT 003: Worker Dispatch (durable)

- run_id: `PDW3-WU2-LEARNER-PRACTICE-REVIEW-TRANSFER-20260812__RETRY-2__20260811T164118Z__8c8d39`
- goal_id: `PDW3-WU2-LEARNER-PRACTICE-REVIEW-TRANSFER-20260812__RETRY-2`
- owner: LEARNER
- worktree: `A:\EAP Agent Project\worktrees\learner`
- branch: `dept/feedback-learner`
- starting_sha: `7a9e4b470c41c0453a3795233f1bdd5c483d80ae`
- checkpoint state: implementation wave dispatched; A/B/C running; D waits
  for A/B/C; V1 waits for D

## 1. Exact route contract

Every smoke/worker launch used:

- CLI: `codex` -> `C:\Users\16073\AppData\Local\hermes\node\codex.cmd`
- CLI version: `codex-cli 0.145.0`
- model: `deepseek/deepseek-v4-flash`
- config: `model_reasoning_effort="ultra"`
- environment: `PLANNING_DISABLED=1`
- worker sandbox: `workspace-write`
- working directory: `A:\EAP Agent Project\worktrees\learner`
- mode: `--ephemeral --json`
- no `opencode-go/mimo-v2.5` substitution

## 2. No-write smoke

Command shape:

```text
$env:PLANNING_DISABLED = '1'
codex exec -m deepseek/deepseek-v4-flash -c 'model_reasoning_effort="ultra"' \\
  -s workspace-write -C 'A:\EAP Agent Project\worktrees\learner' \\
  --ephemeral --json -o '...\dispatch\smoke-retry2-last.txt' \\
  'Reply with exactly the single word PONG and nothing else. Do not read or write any files, do not run any shell commands, and do not use any tools.'
```

Observed result: CLI process completed successfully; JSONL contained
`{"type":"item.completed","item":{"type":"agent_message","text":"PONG"}}`
and `{"type":"turn.completed",...}`. The proxy first returned websocket
HTTP 426 and the CLI fell back to HTTP; the model response still completed.
The previous smoke attempt lacked the output directory; the retry ran after
`dispatch\` was created and reached the model successfully. MCP shutdown
handshake warnings were emitted after the completed turn and did not change
the response result.

## 3. Packet transport recovery

The first A/B/C launch used `Get-Content -Raw packet | codex exec ... -` and
each Windows shim returned the exact error:

```text
node.exe : No prompt provided via stdin.
At C:\Users\16073\AppData\Local\hermes\node\codex.opencodex-real.ps1:16 char:5
```

No A/B/C worker process or product write resulted from that attempt. The
packets were relaunched by reading each packet into `$prompt` and passing it as
the direct `codex exec` prompt argument. This is the chosen path's Windows
transport repair; model/provider/reasoning remained unchanged.

## 4. Active third-level workers

| Worker | Packet | Owned scope | Session ID | Launch result |
| --- | --- | --- | --- | --- |
| A | `packets/A-PRACTICE-REVIEW-EVIDENCE.md` | Practice/review bridge, learner CORE adapter, focused evidence tests | `62757` | RUNNING |
| B | `packets/B-JOURNEY-HISTORY-TRANSFER.md` | Journey practice-history/authentic-application projections, focused tests | `61160` | RUNNING |
| C | `packets/C-LONGITUDINAL-ACKNOWLEDGEMENT.md` | Acknowledgement contracts/router/safety tests | `77730` | RUNNING |

Each launch created its own `workers/<letter>/stdout.jsonl`,
`stderr.log`, and `last-message.txt` output locations. No worker owns another
worker's source or focused test files.

## 5. Next action

Poll A/B/C until each produces a terminal result and findings file. Verify
their actual diffs and focused tests. Then dispatch Worker D with the exact
same model/effort contract for `app/api/main.py`/`deps.py` composition only.
After D, run the affected regression and dispatch a fresh V1 read-only
verifier. Any worker failure will be recorded exactly; no silent model or
provider substitution is allowed.

## 6. Resource/scope status

No Program Control file, other worktree, CORE implementation, migration,
commit, push, PR, merge, promotion, reset, clean, restore, rebase, or raw
SWECCL path was touched. The five pre-existing LEARNER untracked evidence/test
paths remain preserved; the new checkpoint/packet/worker evidence is inside
the authorized learner worktree.

