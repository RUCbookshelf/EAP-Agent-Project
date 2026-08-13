# PDW3-WU2 LEARNER RETRY-2 - CHECKPOINT 002: Dispatch-Surface Exploration (durable)

- run_id: `PDW3-WU2-LEARNER-PRACTICE-REVIEW-TRANSFER-20260812__RETRY-2__20260811T164118Z__8c8d39`
- goal_id: `PDW3-WU2-LEARNER-PRACTICE-REVIEW-TRANSFER-20260812__RETRY-2`
- owner: LEARNER (Feedback & Learner Intelligence)
- worktree: `A:\EAP Agent Project\worktrees\learner`
- branch: `dept/feedback-learner`
- starting_sha: `7a9e4b470c41c0453a3795233f1bdd5c483d80ae`
- checkpoint written: 2026-08-12 (Asia/Shanghai), before any product write
- authority: `executor-prompt.md` (PROGRAM LIVE OVERRIDE, read first) + user-authorized RETRY-2

## 1. Exploration objective

Bounded, read-only discovery of the available way to dispatch new third-level
nested agents from this parent session. No product file, Program Control
artifact, Git state, or provider/model routing was modified during
exploration.

## 2. Exposed tool surface (exact observations)

- In-session multi-agent spawn tool `multi_agent_v1__spawn_agent`: **NOT
  exposed** in this session (absent from the toolset; no `tool_search`
  available). This matches the known tool-availability variance recorded in
  RETRY-1 checkpoint-001.
- Direct probe of the exact tool name `multi_agent_v1__spawn_agent`
  (model=`deepseek/deepseek-v4-flash`, reasoning_effort=`ultra`,
  fork_context=false, no-write smoke task): **CANNOT BE INVOKED** — the
  function is absent from this session's tool schema, so the harness rejects
  the call before dispatch. The exposed-tool enumeration (this session's
  function schema plus the `codex_apps`/`gitnexus` MCP resource list) contains
  no `spawn_agent`-named tool and no tool-search/filter surface. Result:
  ERROR/unavailable; no smoke task was run through that tool and no model was
  substituted.
- Local CLI: `codex` resolves to
  `C:\Users\16073\AppData\Local\hermes\node\codex.cmd`
  (`Get-Command codex` and `where.exe codex` both confirm; the AppX launcher
  `C:\Program Files\WindowsApps\OpenAI.Codex_26.803.10989.0_x64__2p2nqsd0c76g0\app\resources\codex.exe`
  is also on PATH).
- `codex --version` -> `codex-cli 0.145.0`.
- `codex exec --help` confirms the flags needed for bounded nested dispatch:
  `-m/--model`, `-c key=value` config overrides, `-s/--sandbox`, `-C/--cd`,
  `--json`, `--ephemeral`, `-o/--output-last-message`,
  `--output-schema`, `--skip-git-repo-check`.
- `opencodex`, `ocx`, `opencode`: **NOT on PATH** (`Get-Command` and
  `where.exe` returned no matches; recursive search of
  `C:\Users\16073\AppData\Local\hermes` and `C:\Users\16073\.local\bin` for
  `ocx*` found none). RETRY-1 checkpoint-001's `ocx agent status` path was not
  present in this session's PATH.

## 3. Local provider/proxy (exact observations)

- OpenCodex proxy is live at `http://127.0.0.1:10100`:
  - `GET /health` -> HTTP 200 (opencodex proxy dashboard).
  - `GET /v1/models` -> HTTP 200 JSON model list.
- `C:\Users\16073\.codex\config.toml` (read-only) contains:
  - `openai_base_url = "http://127.0.0.1:10100/v1"`
  - `model_catalog_json = "C:\Users\16073\.codex\opencodex-catalog.json"`
  - `[agents] default_subagent_model = "opencode-go/deepseek-v4-flash"`,
    `default_subagent_reasoning_effort = "ultra"`, `max_threads = 16`,
    `max_depth = 2`.
- `/v1/models` advertises exactly the required route:
  `deepseek/deepseek-v4-flash` (owned_by `deepseek`, advertised reasoning
  efforts high/xhigh/max) and its opencode-go alias
  `opencode-go/deepseek-v4-flash` (owned_by `opencode`, same effort list).
  The catalog defines slug `deepseek/deepseek-v4-flash` at
  `opencodex-catalog.json:678` with base instructions identifying as
  deepseek-v4-flash. No other provider/model was substituted in this
  exploration.

## 4. Model/effort contract and chosen dispatch path

- Override requirement: parent and every worker must run
  `deepseek/deepseek-v4-flash` with reasoning `ultra`; nested workers start
  with `PLANNING_DISABLED=1`. No provider or reasoning-mode substitution is
  permitted.
- Chosen dispatch path: `codex exec` (CLI 0.145.0) per third-level worker:

```text
$env:PLANNING_DISABLED = "1"
codex exec -m deepseek/deepseek-v4-flash -c model_reasoning_effort="ultra" `
  -s danger-full-access -C "A:\EAP Agent Project\worktrees\learner" `
  --ephemeral --json -o <worker-result-file> <task-packet-file>
```

- The local proxy performs the ultra injection for the deepseek route
  (observed `default_subagent_reasoning_effort = "ultra"`); the advertised
  effort list on the model object is high/xhigh/max, so the worker run itself
  is the source of truth and will be recorded in each worker's result.

## 5. Next action

1. Finalize disjoint task packets (slices A-D from checkpoint-001 inventory,
   plus the V1 independent read-only verifier) under
   `docs/integration/pdw3-wu2-learner-20260812/packets/`.
2. Run one no-write CLI smoke task through `codex exec` with
   `deepseek/deepseek-v4-flash` + ultra to verify the path end-to-end; record
   the exact command, exit code, and model/effort observed.
3. Dispatch slices A-D as parallel third-level workers using the exact command
   above; each writes only its owned disjoint files and returns a compact
   result + findings file.
4. Collect results; run focused WU2 tests plus the affected Wave-2 regression.
5. Dispatch V1 independent read-only verifier.
6. Write one canonical handoff JSON + Markdown under
   `docs/integration/pdw3-wu2-learner-20260812/` and return it.
7. If any worker cannot start with the exact `deepseek/deepseek-v4-flash` +
   `ultra` route, record the precise provider/model/effort error and return a
   terminal RED handoff rather than substituting.

## 6. Resource hygiene

Exploration was read-only: zero product writes, zero Program Control writes,
zero Git mutations, no raw SWECCL access, no other worktree touched, no
subprocess launched. All five pre-existing untracked LEARNER evidence/test
paths remain byte-preserved.
