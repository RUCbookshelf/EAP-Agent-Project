# PDW1-ALIGN-CORE-B6FCE9 — Safe-alignment evidence report (CORE)

- Goal: `PDW1-ALIGN-CORE-B6FCE9` — Safe-align canonical CORE worktree to Product Delivery Wave 1 baseline
- Owner: CORE
- Executor: opencode-go/deepseek-v4-flash (ultra reasoning), PLANNING_DISABLED=1, evidence-preserving safe-alignment only
- Completed: 2026-08-09
- Verdict: **GREEN**

## Scope

Single authorized mutation: `git merge --ff-only master` inside the canonical CORE worktree. No product-content edits, no promotion, no push, no PR, no master/ref/history/raw-corpus mutation, no nested workers.

## Before-mutation evidence

| Check | Result |
| --- | --- |
| Worktree | `A:\EAP Agent Project\worktrees\shared-core` (git toplevel confirmed) |
| Branch | `dept/shared-core` (exact authorized branch) |
| HEAD | `3f984a94c936df7306f638aa659989bb076a100d` (= packet `promoted_baseline`) |
| Tracked dirt | zero (`git status --porcelain=v1` showed only 4 `??` entries, no staged/modified tracked paths) |
| Ancestor proof | `git merge-base --is-ancestor 3f984a9 b6fce9` exit 0; `git merge-base 3f984a9 b6fce9` = `3f984a9` |
| Master ref | `b6fce9a500502c6929fe0a0e8da4748348967426` (verified from worktree and primary repo) |
| Overwrite proof | `git diff --name-only 3f984a9 b6fce9` = 54 paths; intersection with untracked set (4 files) and ignored set (`.pytest_cache/`, `__pycache__/`, `research_exports/`) = empty |
| Locks | none in `.git/worktrees/shared-core` or main `.git` |

### Pre-existing untracked evidence fingerprints (SHA-256)

| Path | Size (bytes) | SHA-256 |
| --- | --- | --- |
| `docs/architecture/ADR-01-single-runtime-extension-contract.md` | 5615 | `5F887878BB9CB23F9300E69054911B379F753107209A523071ACBDAF59F74023` |
| `docs/architecture/ADR-02-registry-federation-contract.md` | 5956 | `98226D3946E0243EAC57DD612CA2A9941BD83C50236E19660DAF1ECF20809DD4` |
| `docs/architecture/ADR-08-skills-mcp-security-contract.md` | 5330 | `E5B6567483599E0E02A627CAA0CDF91262961D5F494B4E6B967571BF1E176D23` |
| `docs/integration/D09-EPISTEMIC-STATUS-MIGRATION-DESIGN.md` | 24211 | `BFF0D9BF86B091C382C484B62A71AD3A54A95EA9D54BFD0263D9A3981FC9DEF8` |

## Mutation

`git merge --ff-only master` — `Updating 3f984a9..b6fce9a`, fast-forward, 54 files changed (+7060/−31), no merge commit, no rebase, no reset.

## After-mutation evidence

| Check | Result |
| --- | --- |
| HEAD | `b6fce9a500502c6929fe0a0e8da4748348967426` (exact acceptance SHA) |
| Branch | `dept/shared-core` |
| Tracked dirt | zero; `git status --porcelain=v1` identical to before (same 4 untracked entries only) |
| Untracked fingerprints | all 4 SHA-256 + sizes byte-identical to before |
| Master ref | unchanged `b6fce9a500502c6929fe0a0e8da4748348967426` |
| Tree parity | `git diff --stat master HEAD` empty (worktree tree = master tree) |
| Locks / processes | no `.lock` files in worktree gitdir or main `.git`; no `git*` processes running |
| Ref history | HEAD log: `b6fce9a` (CORPUS WU-D merge) ← `e221699` (LEARNER merge) ← `ec39f38` (L2 recovered merge) |

## Outcome

Canonical CORE worktree is safely aligned to promoted master `b6fce9`. WU-0 prerequisite for CORE is closed: the department is ready for a separately authorized write Goal (WU-C Existing-Runtime Agent Capability Execution v1) under qualified ADR constraints and the Product Delivery Wave 1 boundary. No promotion was performed or requested; `promotion_eligible` is false by gate definition (safe-alignment Goal, not a promotion qualification).
