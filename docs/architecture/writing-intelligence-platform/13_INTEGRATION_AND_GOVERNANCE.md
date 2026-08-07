# 13 — Integration and Governance

## 1. Shared-contract change process (Goal section 29)

Department proposes change → Architecture & Integration impact review → affected departments review → ADR → shared contract update → implementation → integration verification. No department may silently change a shared contract. Applies to: shared API schema, shared persistence contracts, shared evidence schema, WritingProfile/CorpusProfile/FeedbackPolicy interfaces, Journey contract, shared identifiers, cross-domain navigation.

## 2. Cross-department conflict process (Goal section 30)

Conflict evidence → affected departments submit concise positions → Architecture & Integration defines ownership/boundary → ADR recorded → departments continue. Do not reopen the whole architecture for a local conflict. Examples: two departments claiming the same abstraction; Academic Source semantics vs Corpus assumptions; L2 feedback-semantics changes; Frontend requiring state no domain owns.

## 3. Architecture drift detection (Goal section 31)

Trigger review on: duplicated domain services; second competing evidence schemas; new shared abstractions hidden inside one department; direct domain-to-domain internal access; unexpected cyclic dependencies; duplicated shared capability; UI bypass of domain contracts. Office decides: accept divergence / formalize new shared contract / move capability into Shared Core / keep capability domain-specific / revert the drift.

## 4. Migration coordination (Goal section 32)

Any migration affecting more than one department is reviewed by the office: migration owner, migration order, backward compatibility, rollout dependency, rollback requirements, affected departments, integration tests. One additive migration stream; individual departments may not silently introduce shared-schema migrations. Current authority: migration 13; planning-only for 14+.

## 5. Departmental autonomy (Goal section 33)

A department may freely change its internal implementation when it does not alter shared contracts, another department's owned contract, shared schema owned elsewhere, cross-department identifiers, or shared semantic definitions. No Architecture & Integration approval for ordinary local implementation. Core principle: internal implementation is owned locally; shared contracts are governed centrally.

## 6. Two-level GREEN model (Goal sections 34–35)

DEPARTMENT GREEN = the department's own owned scope is verified. It does not mean the combined milestone is integrated. At milestone integration, the Architecture & Integration Gate verifies only cross-department behavior: shared interfaces compatible; schema versions aligned; cross-department identifiers resolve; provenance survives boundaries; ownership intact; no duplicate shared abstraction; dependency direction valid; end-to-end workflow connects; migrations compatible; department assumptions consistent. Use department verification artifacts; only rerun tests covering crossed boundaries or release-level contracts.

## 7. Integration checkpoint types (Goal section 39)

| Checkpoint | When required | Owner | Content |
| --- | --- | --- | --- |
| Department Gate | end of every department Work Unit | department | owned scope verified; local tests; acceptance criteria |
| Cross-Department Contract Gate | any shared-contract change | Architecture & Integration | ADR + affected-department review + contract tests |
| Milestone Integration Gate | milestone combining ≥2 departments | Architecture & Integration | cross-department verification list (section 6); INTEGRATION GREEN decision |
| Release Gate | candidate release | Architecture & Integration + all departments | Tier 4 verification: full required regression, startup/entry, locale alignment, final rendered matrix, migration checks, clean-impact review, doc reconciliation |

Do not require full-system verification after every small Work Unit.

## 8. Parallel development contract (Goal section 38)

- **May operate in parallel:** Shared Platform & Core (H1 shared seams) ∥ Research Evaluation (policies) once vocabularies are frozen; L2 Domain ∥ Academic Domain ∥ Corpus scaffolding in H2 (disjoint owned modules); Frontend research surfaces ∥ domain backends once contracts are frozen.
- **Requires sequential work:** Academic UI after Academic data contracts; corpus learner-facing output after display policy; adaptive personalization after validated measurement; any work touching `app/api/main.py` composition root before consolidation; any migration before Architecture & Integration review.
- **Module/file ownership:** per `10_DEPARTMENT_CHARTERS.md` (owned modules per department). Shared files (registries, contracts, migration stream, locale keys) are owned by Shared Platform & Core; changes go through the shared-contract process.
- **Interface ownership:** Shared Platform & Core owns shared interfaces; domain departments own domain contents; Research Evaluation owns validity policies.
- **Shared-contract proposals:** via the process in section 1; no silent changes.
- **Migration coordination:** via section 4.
- **Integration test triggering:** milestone gates per section 7; cross-boundary suites only.

## 9. ADR policy (Goal section 36)

Material shared decisions require a concise ADR: ADR ID, Date, Status; Problem; Affected departments; Existing contract; Proposed change; Options considered; Decision; Reason; Interfaces affected; Migration impact; Backward compatibility; Required integration tests; Deferred consequences. Routine implementation decisions do not require ADRs. The frozen decision baseline is the canonical `docs/architecture/writing-intelligence-platform/14_ARCHITECTURE_DECISIONS.md`; new ADRs are recorded in the Architecture & Integration runtime session (`.agent-workflow/architecture-integration/`, noncanonical).

## 10. Operating constitution (Goal section 50)

Architecture defines boundaries. Departments own implementation. Shared contracts change through governance. Departments verify themselves. Architecture verifies integration. Architecture remains idle when it is not needed.

## 11. Amendments (Round 4 red team; D-34)

- The Architecture & Integration Office convenes by default only for cross-department contract gates and migration coordination; ADRs are required only for shared-contract changes (internal implementation stays departmental); drift triggers are concrete: contract-test failure, version/registry audit failure, sync-conflict-file drift check (D-27).
- Domain-isolation invariants frozen (D-31): no cross-domain submission in another domain's history/journey/revision-candidates/practice provenance; exports domain-scoped by default and reject mixed input; learner-level endpoints filter by domain; revision candidate selection requires domain equality; each invariant is a named contract test.
- Domain attribution is server-derived (D-21); `task_type` is metadata-only until the legacy mapping decision (D-22); migration 14 ships `CHECK (domain IN ('l2','academic'))` + `DEFAULT 'l2'` additively (D-36).