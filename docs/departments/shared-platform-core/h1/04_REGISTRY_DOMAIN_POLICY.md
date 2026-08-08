# 04 — Registry Domain Policy

**Status:** Draft (WU5-REGISTRY-READINESS)
**References:** D-04, D-05, D-22, D-25, D-26, D-37, RT-17, D-L2-01, D-L2-03

---

## 1. Mechanism / Content Split (D-05, D-26)

The Shared Platform Core provides **mechanism only**. Domain departments provide **content**.

| Layer | Owner | Responsibility |
|-------|-------|----------------|
| Registry mechanism | Shared Core | Namespace validation, axes enforcement, lookup APIs, `select_for_domain` |
| Registry content | Domain departments | Task type entries, dimension entries, metric/analyzer registrations |

H1 implements two namespace-scoped registries (`TaskTypeRegistry`, `FeedbackDimensionRegistry`) and one additive domain-selection wrapper (`select_for_domain`).

---

## 2. Namespace Rules

### 2.1 Registered Namespaces

Only two namespaces are registered in H1:

- `l2` — L2 English writing feedback (default, functional)
- `academic` — Academic writing (reserved, NOT functional in H1)

Unknown namespaces are **rejected** at registration time.

### 2.2 Cross-Namespace Isolation

Entries are keyed by `(namespace, task_type_id)`. The same `task_type_id` can exist in multiple namespaces without collision. Cross-namespace duplicate rejection applies only within a single namespace.

---

## 3. TaskTypeRegistry (D-04, D-22)

### 3.1 Metadata-Only Rule (D-22)

The TaskTypeRegistry stores **metadata only**. It must NOT store:

- A comparability predicate between task types
- Any ordering or ranking semantics
- Content that implies ability comparisons

### 3.2 `legacy_unclassified` (D-22)

`legacy_unclassified` is an explicit sentinel value for task types that cannot be classified under the current L2 task-type taxonomy. It is registered in the `l2` namespace with `blocked_by: "D-L2-01"` metadata.

### 3.3 Blocked Content (D-L2-01, D-L2-03)

- **D-L2-01**: L2 task-type enumeration content is blocked pending Researcher decision.
- **D-L2-03**: Academic task taxonomy content is blocked pending Researcher decision.

The Shared Core provides the mechanism with explicit empty/None content for both namespaces.

---

## 4. FeedbackDimensionRegistry (D-37, RT-17)

### 4.1 Axes

Each dimension entry carries two orthogonal axes:

| Axis | Values | Meaning |
|------|--------|---------|
| `availability` | `available` \| `insufficient_evidence` \| `not_applicable` | Whether the dimension is functionally available |
| `learner_exposure` | `student` \| `research_only` | Whether students can see it or it is research-only |

### 4.2 Content Evidencing

Content entries exist **only** where directly evidenced by current code/docs:

- `cohesion` — evidenced by `app/analysis/connective_features.py`
- `lexical_repetition` — evidenced by `app/analysis/lexical_features.py`
- `sentence_structure` — evidenced by `app/analysis/syntactic_features.py`
- `lexical_diversity` — evidenced by `app/calf/` metrics
- `accuracy` — `insufficient_evidence` (annotation foundation only, no automatic measure)
- `fluency` — `research_only` (descriptive proxy only)

Un-evidenced dimensions are left empty with an NR note.

---

## 5. `select_for_domain` Semantics

### 5.1 Additive Wrapper

`select_for_domain(entries, domain)` is an **additive wrapper** that:

- Filters entries to those compatible with the specified domain
- Does NOT modify the underlying registries or their lookup methods
- Does NOT change existing caller behavior

### 5.2 H1 Semantics

- `Domain.L2`: returns all entries (with or without a domain tag)
- `Domain.ACADEMIC`: returns only entries explicitly tagged `"academic"` (currently always empty)

Entries without an explicit domain tag are treated as l2-compatible by default.

### 5.3 Usage Pattern

```python
from app.domain.registry_policy import select_for_domain
from app.domain.domain import Domain

# Filter existing registry entries by domain.
l2_specs = select_for_domain(all_specs, Domain.L2)
academic_specs = select_for_domain(all_specs, Domain.ACADEMIC)
```

---

## 6. Resource-Requirement Selection (D-25)

`select_resource_requirement(specifications, resource_requirement)` filters CALF `MeasurementSpecification` entries by a specific resource requirement. This is a **mechanism-only** helper; no content decisions are made.

```python
from app.domain.registry_policy import select_resource_requirement

spacy_specs = select_resource_requirement(all_specs, "spacy")
```

---

## 7. Blocked Content Summary

| Block | Scope | Status |
|-------|-------|--------|
| D-L2-01 | L2 task-type enumeration | Researcher decision required |
| D-L2-03 | Academic task taxonomy | Researcher decision required |

Shared Core provides mechanism only. Domain packs (WU6) will provide content when Researcher decisions are available.
