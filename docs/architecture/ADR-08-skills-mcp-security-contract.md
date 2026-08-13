 # ADR-08: Skills/MCP Security Requirements Contract
 
 **Goal ID:** CORE-AGENT-CONTRACTS  
 **ADR:** ADR-08 (Skills/MCP Security)  
 **Status:** Phase-A Contract Design  
 **Date:** 2026-08-09  
 **Owner:** CORE  
 
 ## 1. Context
 
 The platform will eventually support Skills and MCP (Model Context Protocol) extensions. DeepTutor’s Skills/MCP ecosystem includes manifest‑first loading, progressive disclosure, sandboxing, and dispatch‑time authorization. This contract defines the **deny‑by‑default** security model that all extensions must follow.
 
 ## 2. Core Principle: Deny‑by‑Default
 
 Every extension starts with **no permissions**. It must explicitly declare and be granted the minimum set of capabilities required for its function.
 
 ## 3. Required Extension Metadata
 
 Each extension must provide a manifest containing:
 
 | Field | Description |
 |-------|-------------|
 | **Identity** | Globally unique name (e.g., `skill:grammar-checker`). |
 | **Version** | Semantic version (`x.y.z`). |
 | **Owner** | The department or author responsible. |
 | **Source** | Origin (e.g., `builtin`, `user`, `marketplace`). |
 | **Capability Scope** | What the extension can do (e.g., `read:text`, `write:text`, `call:api`). |
 | **Domain Eligibility** | Which domains the extension may operate in (e.g., `["l2"]`). |
 | **Data‑Access Scope** | Which data the extension may read/write (e.g., `submissions`, `learner_profiles`). |
 | **Network Scope** | Allowed network destinations (e.g., `none`, `api.openai.com`). |
 | **Filesystem Scope** | Allowed filesystem paths (e.g., `none`, `/tmp/skill-workspace`). |
 | **Consent** | Whether user consent is required before execution. |
 | **Audit** | Whether invocation logs are required (default: true). |
 | **Revocation** | Whether the extension can be disabled at runtime. |
 | **Secret Isolation** | How secrets (API keys, tokens) are provided (e.g., `env`, `vault`). |
 | **Failure Isolation** | Whether the extension runs in a separate thread/process. |
 
 ## 4. Security Lifecycle
 
 | Phase | Requirement |
 |-------|-------------|
 | **Registration** | Extension manifest is validated against the schema. Missing fields are rejected. |
 | **Authorization** | At startup, the composition root reviews requested permissions and grants/denies based on policy. |
 | **Invocation** | At dispatch time, the runtime checks that the requested operation is within the granted scope. |
 | **Audit** | Every invocation is logged with request ID, extension identity, operation, and outcome. |
 | **Revocation** | The runtime can disable an extension; subsequent invocations are rejected. |
 | **Failure Isolation** | Extension failures are caught and logged; the application continues. |
 
 ## 5. Data‑Access Enforcement
 
 - Extensions may only access data explicitly listed in their `data‑access scope`.  
 - Access is checked at the service layer (e.g., before a database query).  
 - Violations are logged and return a `403 Forbidden`.  
 
 ## 6. Network & Filesystem Enforcement
 
 - **Network:** Outbound connections are blocked unless the destination is in the `network scope`.  
 - **Filesystem:** File operations are blocked unless the path is in the `filesystem scope`.  
 - Enforcement can be achieved via OS‑level sandboxing (containers, seccomp) or application‑level wrappers.  
 
 ## 7. Secret Management
 
 - Secrets are injected via environment variables or a secret manager; extensions cannot read arbitrary env vars.  
 - Secrets are scoped to the extension and not shared.  
 - Secrets are rotated on extension update.  
 
 ## 8. Audit & Compliance
 
 - All extension invocations are logged in an append‑only audit table.  
 - Logs include: timestamp, request ID, extension identity, operation, result, and any errors.  
 - Audit logs are retained for a configurable period (default: 30 days).  
 
 ## 9. Trade‑offs & Risks
 
 | Choice | Benefit | Risk | Mitigation |
 |--------|---------|------|------------|
 | Deny‑by‑default | Minimal attack surface. | May require many explicit grants. | Provide sensible default grant sets for common patterns. |
 | Manifest validation at startup | Catches missing fields early. | Startup may be slower. | Validation is fast (schema check). |
 | Audit logging | Compliance and debugging. | Storage overhead. | Rotate logs; compress old logs. |
 | Failure isolation | Stability. | Complexity. | Start with thread isolation; move to process if needed. |
 
 ## 10. Acceptance Criteria
 
 - [ ] Every extension provides a complete manifest.  
 - [ ] The composition root validates manifests at startup.  
 - [ ] Extensions start with no permissions.  
 - [ ] Each permission is explicitly granted.  
 - [ ] Invocations are checked against granted permissions.  
 - [ ] All invocations are logged.  
 - [ ] Extensions can be revoked at runtime.  
 - [ ] Extension failures do not crash the application.  
 
 ## 11. Next Phase (Implementation)
 
 Phase‑B will implement:
 1. A manifest schema (JSON/YAML).  
 2. A permission grant/deny configuration file.  
 3. A runtime permission checker (decorator/wrapper).  
 4. An audit logging middleware.  
 5. A secret injection mechanism.  
 
 ---
 
 **Document version:** 1.0  
 **Classification:** Phase‑A contract design – no implementation.  
