# Corpus Intelligence / corpus_query Boundary Contract (ADR-06)

**Goal ID:** CORPUS-QUERY-BOUNDARY-CONTRACT  
**Owner:** CORPUS  
**Branch:** dept/corpus  
**Worktree:** A:\EAP Agent Project\worktrees\corpus  
**Starting SHA:** 5aafe2728d7135212bd675a6975b44bcf99ee099  
**Date:** 2026-08-09  

## 1. Purpose

This document defines the Phase‑A design of the **corpus_query boundary contract** for the Corpus Intelligence / corpus_query ADR‑06.  
It specifies:

1. **Governed/versioned artifact crossing rules** – which corpus artifacts may cross the CORPUS boundary and under what metadata.
2. **Approved query‑contract shape** – the canonical request/response schema for corpus_query.
3. **CORPUS‑owned semantics** – what the query contract means and how it differs from generic retrieval.
4. **Testable enforcement criteria** – how the system rejects raw SWECCL paths/handles in generic runtime, retrieval, Skill, and MCP pathways.
5. **Verification plan** – concrete checks that will be performed to validate the contract.

This is a **design‑only** document; no implementation, no Corpus Stage 6, no raw corpus access.

---

## 2. Governed/Versioned Artifact Crossing Rules

### 2.1 Allowed Artifacts

Only the following **CORPUS‑owned, governed/versioned** artifacts may cross the boundary:

| Artifact Type | Version Field | Ownership | Allowed Crossing Direction |
|---------------|---------------|-----------|----------------------------|
| Corpus Reference‑Group Descriptor | ersion:semver | CORPUS | CORPUS → any authorized consumer |
| Corpus Query Contract Schema | schema_version | CORPUS | CORPUS → any authorized consumer |
| Corpus Evidence Snapshot (derived, non‑raw) | snapshot_id | CORPUS | CORPUS → any authorized consumer |
| Corpus Eligibility Label Set | label_set_version | CORPUS | CORPUS → any authorized consumer |

### 2.2 Forbidden Artifacts

The following must **never** cross the boundary:

* Raw SWECCL file paths or directory handles (e.g., A:\[Linguistics Data] Corpus\SWECCL 2.0\…).
* Raw SWECCL file handles, file‑system references, or environment variables that resolve to raw corpus locations.
* Unversioned, unvalidated, or unauthenticated corpus data.

### 2.3 Crossing Metadata

Every artifact crossing the boundary must carry:

`yaml
artifact_type: <type>
version: <semver or snapshot_id>
owner: CORPUS
generated_at: <ISO‑8601>
generator: <script/module that produced the artifact>
integrity: <SHA‑256 of artifact content>
eligibility: <label_set_version or "research_only">
`

### 2.4 Version Evolution

* Any change to artifact shape or semantics requires a **new version** (semver bump).
* Deprecated artifacts remain readable for one major version; after that they are rejected.
* The contract schema itself is versioned (schema_version); consumers must declare the schema version they expect.

---

## 3. Approved Query‑Contract Shape

### 3.1 Request Schema

`json
{
  "": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["query_type", "reference_group", "version"],
  "properties": {
    "query_type": {
      "type": "string",
      "enum": ["reference_group_distribution", "corpus_similarity", "learner_exposure"]
    },
    "reference_group": {
      "type": "object",
      "required": ["id", "version"],
      "properties": {
        "id": { "type": "string", "pattern": "^[a-z0-9-]+$" },
        "version": { "type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$" }
      }
    },
    "version": { "type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$" },
    "parameters": { "type": "object" },
    "auth": {
      "type": "object",
      "required": ["consumer_id", "purpose"],
      "properties": {
        "consumer_id": { "type": "string" },
        "purpose": { "type": "string", "enum": ["research", "feedback", "diagnostic"] }
      }
    }
  }
}
`

### 3.2 Response Schema

`json
{
  "": "https://json-schema.org/draft/2020-12/schema",
+  "type": "object",
+  "required": ["status", "query_type", "reference_group", "version", "generated_at", "result"],
+  "properties": {
+    "status": { "type": "string", "enum": ["success", "error", "denied"] },
+    "query_type": { "type": "string" },
+    "reference_group": { "type": "object" },
+    "version": { "type": "string" },
+    "generated_at": { "type": "string", "format": "date-time" },
+    "result": { "type": "object" },
+    "error": { "type": "string" },
+    "eligibility": { "type": "string", "enum": ["research_only", "feedback", "diagnostic"] },
+    "limitations": { "type": "array", "items": { "type": "string" } }
+  }
+}
+`
+
+### 3.3 Semantic Constraints
+
+* The query **must not** return raw SWECCL text; it returns **derived metrics, distributions, or labels** only.
+* The result must carry eligibility and limitations to prevent over‑interpretation.
+* corpus_distance values must **never** be interpreted as proficiency, mastery, or learning gain.
+* Every response must be auditable: the combination of request parameters + version + generated_at uniquely identifies the result.
+
+---
+
+## 4. CORPUS‑Owned Semantics
+
+### 4.1 Ownership
+
+CORPUS exclusively owns:
+
+* The mapping between raw SWECCL data and governed/versioned artifacts.
+* The logic that produces reference‑group distributions, similarity metrics, and eligibility labels.
+* The versioning and deprecation policy for all corpus artifacts.
+* The right to reject any query that violates the contract or attempts to access raw data.
+
+### 4.2 Semantic Boundaries
+
+* **Corpus Intelligence ≠ Generic Retrieval.** A retrieved sentence is not automatically a valid reference‑group comparison, diagnostic inference, or learner‑facing example.
+* **Reference‑Group Validity** is determined solely by CORPUS‑owned algorithms and versioned reference‑group descriptors.
+* **Eligibility Labels** (e.g., esearch_only) are set by CORPUS and must be respected by all consumers.
+
+### 4.3 Integration Points
+
+CORPUS exposes the query contract through:
+
+* A **CORPUS‑owned Python module** (pp/corpus/intelligence.py) that enforces the contract.
+* A **CORPUS‑owned FastAPI router** (/corpus/query) that validates requests and returns versioned responses.
+* Future **CORPUS‑owned Skill/MCP** wrappers that delegate to the same module.
+
+No other module, router, or skill may implement corpus query logic.
+
+---
+
+## 5. Testable Enforcement Criteria
+
+The following criteria **must** be enforceable via automated tests and runtime checks.
+
+### 5.1 Non‑CORPUS Path/Config/Manifest Scans
+
+| Check | Description | Enforcement Method |
+|-------|-------------|--------------------|
+| **Raw SWECCL Path Scan** | Any code path that contains a literal string matching A:\[Linguistics Data] Corpus\SWECCL 2.0 or environment variable resolving to that path. | Static analysis + drift‑guard test (	est_environment_drift.py). |
+| **Config/Manifest Scan** | Configuration files, manifests, or JSON schemas that reference raw SWECCL locations. | Build‑time validation script (scripts/corpus_readiness/10_version.py). |
+| **Environment Variable Scan** | Any process environment variable (other than CORPUS_ROOT) that resolves to raw SWECCL. | Runtime check at CORPUS module initialization. |
+
+### 5.2 Dispatch Authorization Checks
+
+| Check | Description | Enforcement Method |
+|-------|-------------|--------------------|
+| **Consumer Authorization** | Every corpus_query request must carry a valid uth.consumer_id and uth.purpose that are registered in the CORPUS authorization registry. | Request validation in /corpus/query router. |
+| **Purpose‑Scope Enforcement** | The uth.purpose must match the query_type (e.g., learner_exposure only allowed with purpose=feedback). | Router logic + contract tests. |
+| **Version Compatibility** | Consumer must declare the schema version it expects; mismatch results in 406 Not Acceptable. | Router header validation. |
+
+### 5.3 Contract Tests
+
+| Test | Description | Expected Result |
+|------|-------------|-----------------|
+| **Raw‑Path Rejection** | Attempt to invoke any generic runtime, retrieval, Skill, or MCP tool with a raw SWECCL path/handle. | Tool returns denied with reason aw_source_forbidden. |
+| **Unauthorized Consumer** | Send a query with an unknown consumer_id. | 401 Unauthorized. |
+| **Invalid Purpose** | Send a query with a purpose not in the allowed enum. | 400 Bad Request. |
+| **Schema Mismatch** | Send a request with a schema version not supported by the current CORPUS module. | 406 Not Acceptable. |
+| **Result Integrity** | Verify that the response includes all required fields and that integrity matches the content hash. | 200 OK with valid integrity. |
+| **Eligibility Preservation** | Ensure that a query with purpose=feedback never returns eligibility=research_only without explicit consumer consent. | 200 OK with correct eligibility. |
+
+### 5.4 Runtime Denial Mechanisms
+
+1. **CORPUS Module Initialization**: On import, pp/corpus/intelligence.py scans its own module for raw SWECCL references and raises CorpusIntegrityError if found.
+2. **Router Middleware**: The /corpus/query router checks the request against the authorization registry and schema version before invoking the intelligence module.
+3. **Generic Runtime/Retrieval/Skill/MCP Wrappers**: Any wrapper that attempts to call the intelligence module with raw data is intercepted by a **CORPUS‑owned decorator** that logs the violation and returns denied.
+4. **Static Analysis CI**: A dedicated CI step runs g (ripgrep) across the entire repository for forbidden patterns and fails the build if any are found.
+
+---
+
+## 6. Verification Plan
+
+### 6.1 Pre‑Implementation Verification (Phase‑A)
+
+| Item | Method | Pass Criteria |
+|------|--------|---------------|
+| **Artifact Crossing Rules** | Manual review of this document + ADR‑06 constraints. | All constraints from ADR‑06 are addressed. |
+| **Query Contract Shape** | JSON Schema validation of the request/response schemas. | Schemas are valid JSON Schema draft‑2020‑12. |
+| **Semantics Documentation** | Review by CORPUS owner and INT architect. | No ambiguity in ownership or semantic boundaries. |
+| **Enforcement Criteria** | Each criterion mapped to a test case. | Every criterion has at least one test case. |
+
+### 6.2 Post‑Implementation Verification (Future Goal)
+
+| Item | Method | Pass Criteria |
+|------|--------|---------------|
+| **Static Scan** | Run g for raw SWECCL patterns across the repository. | Zero matches outside pp/corpus/ and scripts/corpus_*. |
+| **Runtime Denial** | Execute the contract tests (Section 5.3). | All tests pass. |
+| **Authorization Check** | Attempt to query with an unauthorized consumer. | Request denied with clear error. |
+| **Version Check** | Attempt to query with an unsupported schema version. | Request denied with 406. |
+| **Integrity Check** | Verify that the response integrity hash matches the content. | Hash matches. |
+| **Eligibility Check** | Verify that eligibility labels are correctly propagated. | Labels match the query purpose. |
+
+### 6.3 Continuous Monitoring
+
+* **Drift‑Guard Test**: 	est_environment_drift.py runs on every CI build to ensure no raw SWECCL paths are introduced.
+* **Authorization Registry Audit**: Monthly review of registered consumers and purposes.
+* **Schema Version Deprecation**: Automated alerts when a schema version approaches end‑of‑life.
+
+---
+
+## 7. Appendices
+
+### A. ADR‑06 Constraints Recap
+
+* Raw SWECCL paths/handles must be rejected by generic runtime, retrieval, Skill, and MCP pathways outside explicitly authorized CORPUS scope.
+* Only governed/versioned corpus artifacts and approved query contracts may cross the CORPUS boundary.
+* Enforcement must be testable.
+* Does NOT authorize Corpus Stage 6.
+
+### B. Related Artifacts
+
+* pp/corpus/intelligence.py – CORPUS‑owned query module (to be implemented).
+* scripts/corpus_paths.py – Portable path resolution for corpus scripts.
+* docs/corpus-intelligence/ – Existing corpus intelligence documentation.
+* docs/integration/ – Integration handoff reports.
+
+### C. Version History
+
+| Version | Date | Author | Changes |
+|---------|------|--------|---------|
+| 1.0.0 | 2026‑08‑09 | CORPUS Agent | Initial Phase‑A design. |
+
+---
+
+**Document Status:** Phase‑A Design Complete  
+**Next Step:** Await Program Control assignment for implementation Goal.
