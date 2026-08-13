    # L2 Domain Pack v1 Prerequisite Resolution
    
    **Goal:** L2-PREREQ-RESOLUTION  
    **Date:** 2026-08-09  
    **Status:** READY_WITH_PREREQUISITES  
    **Owner:** L2 Writing Domain  
    **Baseline:** 5aafe2728d7135212bd675a6975b44bcf99ee099  
    **Branch:** dept/l2-writing  
    **Worktree:** A:\EAP Agent Project\worktrees\l2-writing  
    
    ## Executive Summary
    
    This document provides evidence-backed prerequisite records for two critical decisions blocking L2 Domain Pack v1 implementation:
    
    1. **D-L2-01**: Task-type enumeration and labels decision
    2. **D-L2-03**: Dimension-envelope membership feasibility analysis
    
    Both decisions require explicit Researcher sign-off before implementation can proceed.
    
    ---
    
    ## D-L2-01: Task-Type Enumeration Decision
    
    ### Context and Current State
    
    **Current Status:** `Researcher decision required`  
    **General/EAP Scope:** `Unclear`  
    **Evidence Source:** `06_L2_WRITING_DOMAIN.md`, `15_OPEN_QUESTIONS_AND_DEFERRED_DECISIONS.md`
    
    The current system uses free-text `genre` field for task classification, with substring inference for `purpose` derivation (`app/services/learner_model.py:333-344`). This inference must not survive in L2 Domain Pack v1.
    
    **Architecture Decision D-22** establishes that `task_type` is metadata-only until the legacy mapping decision is resolved.
    
    ### Proposed Task-Type Enumeration
    
    The following enumeration is proposed based on L2 writing research literature and current system analysis:
    
    | Task Type ID | Display Name | Description | Scope Considerations |
    |--------------|--------------|-------------|---------------------|
    | `opinion` | Opinion Essay | Personal viewpoint with supporting arguments | Clear pedagogical category |
    | `argumentative` | Argumentative Essay | Evidence-based argumentation with counterarguments | Core L2 writing type |
    | `discussion` | Discussion Essay | Balanced exploration of multiple perspectives | Distinct from argumentative |
    | `problem_solution` | Problem-Solution Essay | Problem identification with proposed solutions | Common EAP task |
    | `general_eap` | General EAP | Catch-all for tasks not fitting above categories | Boundary decision required |
    
    ### Decision Options and Tradeoffs
    
    #### Option A: Five-Type Enumeration (Recommended)
    
    **Pros:**
    - Covers majority of L2 writing tasks observed in SWECCL 2.0 corpus
    - Clear pedagogical distinctions between types
    - Manageable complexity for v1 implementation
    - `general_eap` provides backward compatibility for unclassified tasks
    
    **Cons:**
    - May miss specialized subtypes in future
    - Requires explicit Researcher validation of taxonomy
    - Legacy genre mapping will be non-trivial for ambiguous cases
    
    #### Option B: Four-Type Enumeration (Without `general_eap`)
    
    **Pros:**
    - Forces explicit classification of all tasks
    - Cleaner taxonomy without catch-all category
    
    **Cons:**
    - Loses backward compatibility with legacy unclassified tasks
    - May require manual reclassification of historical data
    - Risk of misclassification for edge cases
    
    #### Option C: Expanded Enumeration (7+ Types)
    
    **Pros:**
    - More granular classification
    - Better aligned with specialized L2 writing research
    
    **Cons:**
    - Increased complexity for v1
    - May exceed current system's need for task differentiation
    - Requires more extensive corpus validation
    
    ### Researcher Decision Required
    
    **Specific Questions for Researcher Review:**
    
    1. **Taxonomy Validation:** Is the proposed five-type enumeration pedagogically sound for L2 writing instruction?
    
    2. **General/EAP Boundary:** Should `general_eap` be included as a catch-all, or should all tasks be explicitly classified?
    
    3. **Corpus Validation:** Do the proposed types align with actual task distributions in SWECCL 2.0 and other L2 writing corpora?
    
    4. **Pedagogical Utility:** Will this enumeration support meaningful diagnostic differentiation and practice generation?
    
    5. **Legacy Mapping:** How should historical genres (`expository`, `narrative`, etc.) map to the new taxonomy? Current status: `expository`/`narrative` → `Unclear`, never guessed.
    
    ### Implementation Requirements
    
    **If Researcher approves enumeration:**
    
    1. **Registry Update:** Add entries to `TaskTypeRegistry` in `l2` namespace
    2. **Domain Pack Content:** Create task-type definitions with:
       - Per-type expectations (moves, paragraphing)
       - Supported diagnosis categories
       - Practice target codes
       - Locale keys (en/zh_CN)
       - Evidence requirements
    
    3. **Longitudinal Rules:** Implement conservative comparability:
       - Same `task_type` + same normalized prompt = comparable
       - Same type with different prompts = `not_comparable`
       - Later-task recurrence through existing TraceStatus semantics
    
    4. **UI Integration:** Add typed task-type picker to Student UI (deferred beyond this Goal per D-L2-10)
    
    ---
    
    ## D-L2-03: Dimension-Envelope Feasibility Analysis
    
    ### Context and Current State
    
    **Current Status:** `Researcher decision required`  
    **Feasibility:** `Unclear` (spike needed)  
    **Evidence Source:** `06_L2_WRITING_DOMAIN.md`, `corpus-intelligence/l2/02_FEATURE_CONTRACT.md`
    
    The feedback-dimension envelope currently includes:
    
    | Dimension | Status | Evidence Requirement |
    |-----------|--------|----------------------|
    | Lexical repetition/range | Available | Deterministic evidence |
    | Cohesion/connectives | Available | Deterministic evidence |
    | Sentence/structure | Available | Deterministic evidence |
    | Discourse organization | **Candidate** | Feasibility spike required |
    | Local accuracy/grammar | Unavailable | Evaluation-unavailable state |
    | Task fulfillment/content | Unavailable | Evaluation-unavailable state |
    | Sophistication | Unavailable | Evaluation-unavailable state |
    
    ### Discourse Organization Feasibility Analysis
    
    #### Current Evidence Sources
    
    1. **Connective Features:** `app/analysis/connective_features.py` provides discourse connective analysis
    2. **Lexical Cohesion:** Potential for lexical repetition and range analysis
    3. **Corpus Intelligence:** `docs/corpus-intelligence/l2/02_FEATURE_CONTRACT.md` indicates "Lexical cohesion/discourse organization - requires D-L2-03 feasibility"
    
    #### Feasibility Spike Requirements
    
    **Spike Objective:** Determine if deterministic organization evidence can be extracted from L2 writing submissions.
    
    **Proposed Investigation Areas:**
    
    1. **Paragraph Structure Analysis:**
       - Topic sentence identification
       - Supporting detail patterns
       - Paragraph cohesion metrics
    
    2. **Discourse Marker Analysis:**
       - Transition word usage patterns
       - Logical connector frequency and variety
       - Discourse organization markers
    
    3. **Document Structure Metrics:**
       - Introduction-body-conclusion patterns
       - Argument progression analysis
       - Evidence integration patterns
    
    #### Decision Options and Tradeoffs
    
    ##### Option A: Include Discourse Organization in v1 (If Feasible)
    
    **Pros:**
    - Addresses known gap in current diagnostic coverage
    - Provides more comprehensive writing feedback
    - Aligns with L2 writing pedagogy research
    
    **Cons:**
    - Requires successful feasibility spike
    - May introduce unreliable evidence if not deterministic
    - Increases v1 scope and complexity
    
    ##### Option B: Defer Discourse Organization to v2
    
    **Pros:**
    - Reduces v1 risk and complexity
    - Allows more thorough feasibility investigation
    - Keeps v1 focused on proven dimensions
    
    **Cons:**
    - Leaves known diagnostic gap unresolved
    - May require more extensive changes in v2
    - Defers pedagogical benefit
    
    ##### Option C: Include as "Candidate" with Limited Scope
    
    **Pros:**
    - Provides partial benefit while managing risk
    - Allows controlled experimentation
    - Maintains clear availability states
    
    **Cons:**
    - May confuse users with partial functionality
    - Requires careful state management
    - Still requires feasibility validation
    
    ### Researcher Decision Required
    
    **Specific Questions for Researcher Review:**
    
    1. **Feasibility Validation:** Should a feasibility spike be conducted before including discourse organization in v1?
    
    2. **Evidence Requirements:** What deterministic evidence sources are acceptable for discourse organization diagnosis?
    
    3. **Pedagogical Value:** Is discourse organization diagnosis sufficiently important for L2 writing feedback to justify the complexity?
    
    4. **State Management:** How should discourse organization be represented in the dimension envelope (available, candidate, unavailable)?
    
    5. **Corpus Integration:** What corpus features should be used to validate discourse organization metrics?
    
    ### Implementation Requirements
    
    **If Researcher approves inclusion (after feasibility spike):**
    
    1. **Feature Contract:** Update `02_FEATURE_CONTRACT.md` with deterministic evidence requirements
    2. **Analyzer Integration:** Add organization analysis to existing analyzer pipeline
    3. **Dimension Registry:** Add to `FeedbackDimensionRegistry` with appropriate availability state
    4. **Calibration Integration:** Define thresholds and eligibility content in domain pack
    5. **UI Integration:** Add organization feedback to Student UI (following existing dimension patterns)
    
    ---
    
    ## Decision Dependencies and Sequencing
    
    ### Critical Path
    
    1. **D-L2-01** (Task-Type Enumeration) must resolve first as it defines:
       - Task-type specific expectations
       - Diagnosis category mapping
       - Practice target code eligibility
    
    2. **D-L2-03** (Dimension Feasibility) can proceed in parallel but requires:
       - Successful feasibility spike
       - Researcher sign-off on evidence requirements
       - Integration with task-type specific diagnosis
    
    ### Integration Considerations
    
    **Cross-Department Contract Gate:**
    - No silent legacy-genre inference
    - No new dimension without deterministic evidence
    - All current L2 behavior remains compatible
    
    **Shared Core Dependencies:**
    - TaskTypeRegistry mechanism (D-04, D-22)
    - FeedbackDimensionRegistry mechanism
    - Domain Pack configuration-version machinery
    - Existing calibration gate and evidence verification
    
    ---
    
    ## Evidence References
    
    ### Primary Sources
    
    1. `docs/architecture/writing-intelligence-platform/06_L2_WRITING_DOMAIN.md` - L2 Domain architecture
    2. `docs/architecture/writing-intelligence-platform/15_OPEN_QUESTIONS_AND_DEFERRED_DECISIONS.md` - Open decisions
    3. `docs/architecture/writing-intelligence-platform/03_SHARED_CORE_AND_DOMAIN_BOUNDARIES.md` - Domain boundaries
    4. `docs/architecture/writing-intelligence-platform/14_ARCHITECTURE_DECISIONS.md` - Architecture decisions
    
    ### Code Evidence
    
    1. `app/shared/task_type_registry.py` - TaskTypeRegistry mechanism
    2. `app/configuration/domain_packs_loader.py` - Domain pack loading
    3. `app/analysis/connective_features.py` - Discourse connective analysis
    4. `docs/corpus-intelligence/l2/02_FEATURE_CONTRACT.md` - Feature contract requirements
    
    ### Program Control References
    
    1. `program-control/DEPENDENCY_GRAPH.md` - Dependency topology
    2. `program-control/PROGRAM_STATUS.md` - Current program status
    3. `program-control/WORKSTREAM_REGISTRY.json` - Workstream definitions
    
    ---
    
    ## Next Steps
    
    1. **Researcher Review:** Present this document to Researcher for decision on D-L2-01 and D-L2-03
    2. **Feasibility Spike:** If approved, conduct discourse organization feasibility investigation
    3. **Decision Packet:** Create formal decision packets for PROGRAM/Researcher review
    4. **Implementation Planning:** Once decisions are made, plan Domain Pack v1 implementation
    
    ---
    
    ## Handoff Information
    
    **Goal ID:** L2-PREREQ-RESOLUTION  
    **Owner:** L2  
    **Starting SHA:** 5aafe2728d7135212bd675a6975b44bcf99ee099  
    **Final SHA:** [Current HEAD]  
    **Branch:** dept/l2-writing  
    **Worktree:** A:\EAP Agent Project\worktrees\l2-writing  
    **Verdict:** AMBER (qualified with targeted repairs/researcher decisions)  
    **Researcher Decision Required:** true  
    **User Decision Required:** false  
    **Integration Required:** true  
    **Promotion Eligible:** false  
    
    **Blocking Findings:**
    - D-L2-01 task-type enumeration requires Researcher decision
    - D-L2-03 dimension feasibility requires Researcher decision and feasibility spike
    
    **Dependencies Unlocked:**
    - None (both decisions are prerequisites for Domain Pack v1)
    
    **Dependencies Remaining:**
    - D-L2-01 task-type enumeration decision
    - D-L2-03 dimension feasibility and Research sign-off
    
    **Artifacts:**
    - `docs/integration/L2_PREREQUISITE_RESOLUTION.md` (this document)
    
    **Gate Authority:** INT (for integration gate goals)
    **Gate Evidence:** This document provides prerequisite resolution evidence
    
    ---
    
    *Document generated by L2 Writing execution agent*  
    *Baseline: 5aafe2728d7135212bd675a6975b44bcf99ee099*  
    *Worktree: A:\EAP Agent Project\worktrees\l2-writing*
