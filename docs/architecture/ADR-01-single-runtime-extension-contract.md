 # ADR-01: Single-Runtime Extension Contract
 
 **Goal ID:** CORE-AGENT-CONTRACTS  
 **ADR:** ADR-01 (Single Runtime)  
 **Status:** Phase-A Contract Design  
 **Date:** 2026-08-09  
 **Owner:** CORE  
 
 ## 1. Context
 
 The Writing Intelligence Platform is a single‑process, single‑SQLite, single‑API‑namespace FastAPI application with a single composition root (`app/api/main.py`). DeepTutor’s runtime model includes a separate turn manager, orchestrator, stream bus, and agentic loop, all of which would introduce parallel runtime components and violate the frozen architecture invariant.
 
 This contract defines how future agent capabilities can be added **without** creating a parallel runtime.
 
 ## 2. Retained Concepts from DeepTutor
 
 | Concept | Local Mapping | Rationale |
 |---------|---------------|-----------|
 | **Manifest‑first capability registration** | Additive metadata on existing domain registries (`AnalyzerRegistry`, `ConfigurationRegistry`, `DomainRegistryPolicy`). | Provides version, owner, and eligibility without a new authority. |
 | **Dispatch‑time authorization** | Thin authorization layer in the composition root that checks a capability manifest before delegating to the existing router. | Enforces least‑privilege at the single entry point. |
 | **Scoped registry overlays** | Extend `registry_policy.py` to support multiple scopes (e.g., `l2`, `academic`) while preserving the single source of truth. | Enables domain‑aware discovery without duplicate registration. |
 | **Tool identity/version/permission** | Explicit tool registry as a thin layer over existing FastAPI router functions. | Makes implicit tools explicit and auditable. |
 
 ## 3. Rejected Parallel Mechanisms
 
 The following DeepTutor mechanisms **must not** be introduced as separate runtime components:
 
 | Rejected Mechanism | Reason |
 |--------------------|--------|
 | **Turn manager** | Would create a second request‑lifecycle manager; the existing FastAPI request/response cycle is the turn manager. |
 | **Orchestrator** | The composition root (`app/api/main.py`) is the single orchestrator; a second one would split control. |
 | **Event bus / Stream bus** | FastAPI `StreamingResponse` already handles streaming; a separate bus would create a second communication channel. |
 | **Composition root** | Only one composition root may exist; all service wiring stays in `app/api/main.py`. |
 | **Runtime database** | The single SQLite database remains the only persistence; no second store may be introduced. |
 | **Parallel process** | The application must remain a single OS process; no fork/worker separation is allowed. |
 
 ## 4. Extension‑Point Map
 
 | Extension Need | Existing Entry Point | How to Extend |
 |----------------|----------------------|---------------|
 | New analysis capability | `AnalyzerRegistry` | Register a new analyzer with a manifest (name, version, owner, domain eligibility). |
 | New configuration metric | `ConfigurationRegistry` | Add a metric definition with a manifest. |
 | New API endpoint | FastAPI router in `app/api/routers/` | Add a router; the composition root includes it automatically. |
 | New service | `_build_services` in `app/api/main.py` | Construct the service and attach it to `api.state`. |
 | New domain policy | `DomainRegistryPolicy` | Extend the policy with a new domain tag; the policy already filters by domain. |
 | New tool | Tool registry (future) | Register a tool with identity, version, permission, and audit metadata. |
 
 ## 5. Lifecycle Requirements
 
 1. **Registration** – Every extension must be registered at startup (or lazily on first use) with an explicit manifest.  
 2. **Versioning** – Manifests carry a semantic version; the composition root validates compatibility.  
 3. **Failure isolation** – An extension failure must not crash the process; the composition root must catch and log.  
 4. **Provenance** – All extension invocations must be logged with request ID, extension identity, and outcome.  
 5. **Revocation** – Extensions can be disabled at runtime via configuration; the composition root must respect the flag.  
 
 ## 6. Trade‑offs & Risks
 
 | Choice | Benefit | Risk | Mitigation |
 |--------|---------|------|------------|
 | Thin tool registry over routers | Minimal change; leverages existing routing. | May lack rich metadata. | Add a manifest schema; validate at startup. |
 | No separate turn manager | Preserves single‑process invariant. | Limits long‑running agentic tasks. | Future tasks must be broken into request‑sized units or escalated via an explicit Goal. |
 | Dispatch‑time auth in composition root | Centralized enforcement. | Composition root becomes more complex. | Keep auth logic in a dedicated module; test thoroughly. |
 
 ## 7. Acceptance Criteria
 
 - [ ] All new capabilities are registered via manifests.  
 - [ ] No parallel runtime, orchestrator, or event bus is introduced.  
 - [ ] The single SQLite database remains the only store.  
 - [ ] The composition root (`app/api/main.py`) remains the single wiring point.  
 - [ ] Extensions are isolated: a failure in one does not bring down the whole app.  
 
 ## 8. Next Phase (Implementation)
 
 Phase‑B will implement:
 1. A manifest schema (JSON/YAML) for capabilities and tools.  
 2. A thin tool registry that wraps existing routers.  
 3. Dispatch‑time authorization checks in the composition root.  
 4. Logging and audit hooks for extension invocations.  
 
 ---
 
 **Document version:** 1.0  
 **Classification:** Phase‑A contract design – no implementation.  
