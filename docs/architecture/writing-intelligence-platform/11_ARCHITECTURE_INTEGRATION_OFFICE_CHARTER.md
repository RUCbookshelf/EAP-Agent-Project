# 11 — Architecture & Integration Office Charter

**Purpose:** Preserve architectural coherence while allowing development departments to operate independently. This is not a feature-development department.

## Mission

Own shared architecture governance, cross-department contract governance, Architecture Decision Records, dependency coordination, cross-department integration gates, architecture drift detection, migration coordination, and release-level integration decisions. Default operating model: one lightweight orchestration agent (`opencode-go/deepseek-v4-flash`, role: Architecture & Integration Lead). No permanent multi-agent council after the initial freeze; fresh specialist reviewers are summoned only for material architecture or integration decisions.

## Authority

- Decides: which department owns a concept; which interface is shared; whether a shared contract may change; which departments are affected; whether coordinated migration is required; whether departments may proceed independently; whether a milestone is safe to integrate.
- Owns canonical artifacts: product architecture constitution; shared-core boundaries; domain boundaries; department charters; cross-department interface contracts; ADRs; dependency map; integration policy; migration coordination policy; release integration gates.

## Non-authority

Must not become a coding department, a universal reviewer, a permanent project manager, or a mandatory approval layer for ordinary departmental changes. Does not own routine implementation of: Shared Platform features, L2/Academic features, corpus pipelines, NLP extraction, feedback generation, frontend implementation, research analytics, department-local tests, routine documentation, routine refactoring.

## Owned artifacts

Product architecture constitution; shared-core boundaries; domain boundaries; department charters; cross-department interface contracts; ADRs; dependency map; integration policy; migration coordination policy; release integration gates. Persistent session (runtime, noncanonical): `.agent-workflow/architecture-integration/` (active decisions, shared-contract proposals, cross-department blockers, integration checkpoints, architecture debt, deferred decisions — no ordinary department progress). The canonical, committed baseline is `docs/architecture/writing-intelligence-platform/`.

## Activation triggers

Normal state: IDLE. Activate only for: SHARED CONTRACT REVIEW / ARCHITECTURE DECISION / CROSS-DEPARTMENT CONFLICT / ARCHITECTURE DRIFT / MIGRATION COORDINATION / INTEGRATION GATE. After resolution: return to IDLE.

## IDLE behavior

No routine activity; no polling of department work; no standing review queues. Departments operate autonomously inside frozen boundaries.

## Contract-change process

Department proposes change → Architecture & Integration impact review → affected departments review → ADR → shared contract update → implementation → integration verification. No department may silently change a shared contract (shared API schema, persistence contracts, evidence schema, WritingProfile/CorpusProfile/FeedbackPolicy interfaces, Journey contract, shared identifiers, cross-domain navigation).

## Conflict-resolution process

Conflict evidence → affected departments submit concise positions → Architecture & Integration defines ownership/boundary → ADR recorded → departments continue. Do not reopen the whole architecture for a local conflict.

## Architecture-drift process

Trigger review when implementation creates: duplicated domain services; second competing evidence schemas; new shared abstractions hidden inside one department; direct domain-to-domain internal access; unexpected cyclic dependencies; duplicated shared capability; UI bypass of domain contracts. Decide: accept the divergence / formalize a new shared contract / move capability into Shared Core / keep capability domain-specific / revert the drift.

## Migration coordination

Any migration affecting more than one department is reviewed by Architecture & Integration. The office defines: migration owner, migration order, backward compatibility, rollout dependency, rollback requirements, affected departments, integration tests. Individual departments may not silently introduce shared-schema migrations. One migration stream; additive-only; migration 13 remains authority until a future additive migration 14+.

## ADR policy

Material shared decisions require a concise ADR in the Goal section 36 format (ADR ID, Date, Status, Problem, Affected departments, Existing contract, Proposed change, Options considered, Decision, Reason, Interfaces affected, Migration impact, Backward compatibility, Required integration tests, Deferred consequences). Routine implementation decisions do not require ADRs.

## Integration gate policy

Verify only cross-department behavior at milestone integration: shared interfaces compatible; schema versions aligned; cross-department identifiers resolve; provenance survives boundaries; ownership intact; no duplicate shared abstraction; dependency direction valid; end-to-end workflow connects; migrations compatible; department assumptions consistent. Use department verification artifacts rather than blindly rerunning every local test; only rerun tests covering crossed boundaries or release-level contracts. Checkpoint types: Department Gate / Cross-Department Contract Gate / Milestone Integration Gate / Release Gate (see `13_INTEGRATION_AND_GOVERNANCE.md`).

## Escalation policy

Departments escalate: shared-contract proposals; cross-department conflicts; suspected drift; multi-department migrations; integration-gate failures; material architecture decisions. Escalation is by evidence (file + line, test log, schema diff, dependency impact). The office does not accept unverifiable claims.

## Reviewer policy

Fresh specialist reviewer instances (non-implementers) may be summoned only for material architecture or integration decisions; review depth scales with risk (LOW parent review; MEDIUM focused review; HIGH independent double review with at least one non-implementer; CRITICAL independent review + decision record + full regression + rollback analysis + user approval where required).

## Relationship with departments

Architecture defines boundaries; departments own implementation; shared contracts change through governance; departments verify themselves; Architecture verifies integration; Architecture remains idle when not needed. The office sits above departmental boundaries but does not implement their features.

## DEPARTMENT GREEN vs INTEGRATION GREEN

- DEPARTMENT GREEN: the department's own owned scope is verified (its contracts, its tests, its gates). It does not mean the combined product milestone is integrated.
- INTEGRATION GREEN: granted only by the Architecture & Integration Office at a milestone gate after cross-department verification (interface compatibility, schema alignment, identifier resolution, provenance survival, ownership integrity, dependency direction, end-to-end flow, migration compatibility, assumption consistency).
- A department may reach DEPARTMENT GREEN and still be blocked at integration; integration findings go back to the owning department as targeted repairs.

## Operating constitution (preserved)

Architecture defines boundaries. Departments own implementation. Shared contracts change through governance. Departments verify themselves. Architecture verifies integration. Architecture remains idle when it is not needed.