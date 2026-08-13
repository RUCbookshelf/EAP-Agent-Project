 # ADR-02: Registry Federation Contract
 
 **Goal ID:** CORE-AGENT-CONTRACTS  
 **ADR:** ADR-02 (Registry Federation)  
 **Status:** Phase-A Contract Design  
 **Date:** 2026-08-09  
 **Owner:** CORE  
 
 ## 1. Context
 
 Existing authoritative domain registries (`AnalyzerRegistry`, `ConfigurationRegistry`, `DomainRegistryPolicy`) own their respective domains. DeepTutor’s capability/tool discovery uses manifest‑first loading and scoped overlays. This contract defines a federation/adapter layer that allows cross‑domain discovery **without** replacing the existing registries.
 
 ## 2. Design Principles
 
 1. **Authority Preservation** – Each domain registry remains the single source of truth for its entries.  
 2. **Federation as Read‑Only Adapter** – The federation layer only reads from existing registries; it does not write back.  
 3. **Precedence** – Domain‑specific entries always take precedence over federated entries.  
 4. **Duplicate‑Registration Protection** – The federation layer rejects entries that conflict with an existing domain entry (same identity + version).  
 5. **Version Compatibility** – Each entry carries a semantic version; the federation layer can filter by compatibility ranges.  
 6. **Rollback** – The federation layer can be disabled without affecting the underlying registries.  
 
 ## 3. Architecture
 
 ```text
 ┌─────────────────────────────────────────────────────┐
 │                  Application Layer                  │
 │  (FastAPI routers, services, composition root)      │
 └───────────────────────┬─────────────────────────────┘
                         │  query
                         ▼
 ┌─────────────────────────────────────────────────────┐
 │              Federation Adapter (Read‑Only)         │
 │  • Merges results from multiple registries          │
 │  • Applies precedence rules                         │
 │  • Filters by domain eligibility                    │
 │  • Enforces version compatibility                   │
 └───────────┬──────────────────┬──────────────────────┘
             │                  │
             ▼                  ▼
 ┌────────────────────┐ ┌────────────────────────────┐
 │  AnalyzerRegistry  │ │  ConfigurationRegistry     │
 │  (L2‑only)         │ │  (L2‑only)                 │
 └────────────────────┘ └────────────────────────────┘
             │                  │
             ▼                  ▼
 ┌────────────────────┐ ┌────────────────────────────┐
 │  DomainRegistry    │ │  Future Registries         │
 │  Policy (L2)       │ │  (Academic, etc.)          │
 └────────────────────┘ └────────────────────────────┘
 ```
 
 ## 4. Federation Rules
 
 | Rule | Description |
 |------|-------------|
 | **Identity** | Each entry must have a globally unique `id` (e.g., `analyzer:spacy`). |
 | **Version** | Entries must carry a semantic version (`x.y.z`). |
 | **Owner** | The registry that owns the entry (e.g., `analyzer`, `config`). |
 | **Domain Eligibility** | Each entry declares one or more domains (e.g., `["l2"]`). |
 | **Precedence** | If two entries share the same `id`, the one from the domain‑specific registry wins. |
 | **Compatibility** | The federation layer can request entries compatible with a version range (e.g., `>=1.0,<2.0`). |
 | **Duplicate Rejection** | If a federated entry conflicts with a domain entry (same `id` + `version`), the federation layer logs a warning and discards the federated entry. |
 
 ## 5. Rollback & Failure
 
 - The federation layer is optional; it can be disabled via configuration.  
 - If the federation layer fails, the application falls back to direct registry lookups (existing behavior).  
 - No data is lost because the layer is read‑only.  
 
 ## 6. Trade‑offs & Risks
 
 | Choice | Benefit | Risk | Mitigation |
 |--------|---------|------|------------|
 | Read‑only federation | No risk to authoritative data. | May not support write‑back scenarios. | Write‑back is not required in Phase‑A. |
 | Precedence by domain | Clear ownership. | May hide federated entries unexpectedly. | Log precedence decisions; provide a debug endpoint. |
 | Version compatibility filtering | Enables safe upgrades. | Adds complexity. | Keep filter logic simple (semver ranges). |
 
 ## 7. Acceptance Criteria
 
 - [ ] Existing registries remain authoritative.  
 - [ ] The federation layer is read‑only.  
 | - [ ] Precedence rules are enforced (domain > federation). |  
 | - [ ] Duplicate‑registration attempts are logged and rejected. |  
 | - [ ] The federation layer can be disabled without side effects. |  
 
 ## 8. Next Phase (Implementation)
 
 Phase‑B will implement:
 1. A `FederationAdapter` class that queries multiple registries.  
 2. A configuration flag to enable/disable federation.  
 3. Precedence and duplicate‑detection logic.  
 4. Logging for precedence decisions and rejections.  
 
 ---
 
 **Document version:** 1.0  
 **Classification:** Phase‑A contract design – no implementation.  
