# 03 — Corpus Use and Licensing Policy

**Department:** Research Evaluation & Data Governance
**Policy id:** `corpus-use-policy-v0.1.0`
**Ratification:** RD-POL-003 (2026-08-07)
**Status:** RATIFIED
**Supersedes:** none (first canonical version)

## 1. Canonical license status

```text
license_status = PARTIALLY_DOCUMENTED
```

Evidence: the corpus ships as a published book (SWECCL 2.0, ISBN 978-7-5600-8015-4,
FLTRP 2008-12) with a copyright page but no explicit corpus-use license in the manual
(`docs/corpus-readiness/sweccl2/11_LIMITATIONS_AND_OPEN_ISSUES.md:43-48`); the registered
package record carries `license_status: "PARTIALLY_DOCUMENTED; external use REQUIRES_REVIEW"`
(`docs/corpus-readiness/sweccl2/corpus_version.json`; `docs/corpus-intelligence/l2/01_CORPUS_RESOURCE_REGISTRATION.md`).
This status is a documented fact, not a legal opinion. This policy does not invent legal
rights: no state below asserts a grant or a prohibition that the documentation does not
support.

## 2. Authorization-state model

| State | Meaning | Default posture |
| --- | --- | --- |
| `ALLOWED` | The operation is documented as permitted and the platform policy permits it. | May proceed under the platform's standard guards. |
| `REQUIRES_REVIEW` | No explicit permission is documented for this operation; the platform policy does not authorize it by default. | Blocked until a named review (researcher + owner/legal where applicable) records an explicit decision with evidence. |
| `PROHIBITED` | A documented prohibition or a platform structural prohibition applies. | Never performed; a policy change is required first. |
| `UNKNOWN` | No documentation exists to classify the operation. | Not performed; the item stays on the open-decision register (D3 family). |

## 3. Operation × state matrix

| Operation | State | Evidence |
| --- | --- | --- |
| Local deterministic analysis (feature extraction, distributions, query boundary over prepared texts) | `ALLOWED` | "Local preparation, analysis, and descriptive reporting are permitted" — RD-11:43-48; Stage-5 implemented fully locally (L2-00; L2-09). |
| Aggregate internal statistics (descriptive reference distributions, internal research reporting, no raw text) | `ALLOWED` | RD-11:43-48; distributions contain statistics only, no raw text (L2-06; L2-07 safety). |
| Research/development use inside the platform (internal pipeline, `learner_exposure=research_only`) | `ALLOWED` | RD-11:43-48; D-08 research-first posture (ARCH-14:77-84); every query result carries research_only (L2-07). |
| External redistribution (corpus texts, derived raw texts, or unrestricted excerpts to third parties) | `REQUIRES_REVIEW` | "external distribution or learner-facing use REQUIRES_REVIEW" — RD-11:45-48; no raw corpus content in git (RD-00 key constraints; corpus_version.json). |
| Learner-facing raw examples (authentic corpus excerpts shown to learners) | `REQUIRES_REVIEW` | D-08 default disabled; any learner exposure requires a Researcher decision, display policy, and licensing/anonymization gate (ARCH-14:77-84); RD-11:45-48. |
| External API upload (sending corpus texts to third-party services) | `REQUIRES_REVIEW` | "no external uploads" privacy constraint — `docs/corpus-readiness/sweccl2/12_L2_CORPUS_IMPLEMENTATION_HANDOFF.md` (licensing/privacy constraints); sensitive research data treatment — same source. |
| Model training / fine-tuning on corpus texts | `REQUIRES_REVIEW` | No explicit training grant is documented (RD-11:43-48); copyright page only. Review must record the legal basis before any training use. |
| Public release (publishing corpus or raw derived texts) | `REQUIRES_REVIEW` | RD-11:45-48; no explicit release grant documented. |
| Publishing raw corpus text into the repository or reports | `PROHIBITED` (structural) | "No raw texts in reports; no commits of raw corpus content or derived texts" — RD-00 key constraints; I2 corpus read-only (ARCH-07:28). |
| Unrestricted corpus-example exposure through the query boundary | `PROHIBITED` (structural) | "No unrestricted corpus examples are exposed (licensing policy: not permitted at PARTIALLY_DOCUMENTED status)" — L2-07 safety; learner exposure structurally research_only. |
| Writing learner text into the corpus or mutating corpus artifacts | `PROHIBITED` (structural) | I2 — corpus is read-only reference data (ARCH-07:28). |
| Commercial exploitation / sub-licensing / derivative corpus publication | `UNKNOWN` | No documentation in the manual (RD-11); D3 licensing model is a Researcher decision (ARCH-15:43). |

## 4. Review path for `REQUIRES_REVIEW` operations

1. A named requester records the operation, purpose, data scope, and requested state.
2. Research Evaluation & Data Governance reviews against this policy and the documented
   evidence; for operations with legal significance (redistribution, training, release),
   the review must record the legal basis (owner grant, license text, or explicit
   researcher decision with justification) — no review may assert a right that the
   documentation does not support.
3. The decision is recorded as a versioned amendment to this policy or as an
   `UNKNOWN→REQUIRES_REVIEW`/`ALLOWED` transition in `policy_registry.json` with new
   evidence.
4. Any learner-facing outcome additionally requires the D-08 display policy and
   licensing/anonymization gate (ARCH-14:77-84).

## 5. Non-negotiable platform constraints (regardless of state)

- Corpus is read-only reference data; learner text never enters the corpus (I2, ARCH-07:28).
- No raw corpus content in git; derived texts stay outside the repository (RD-00).
- Corpus texts are sensitive research data: no PII propagation; no external uploads;
  learner-typed Chinese characters and transcriber notes handled as content, never
  published raw (docs/corpus-readiness/sweccl2/12_L2_CORPUS_IMPLEMENTATION_HANDOFF.md).
- Learner-facing corpus content is disabled by default; all current query results are
  `research_only` (D-08; L2-07).

## 6. Open items (not resolved here)

- D3 — licensing/permission model per corpus: `Researcher decision required`
  (ARCH-15:43); this policy remains `PARTIALLY_DOCUMENTED` until a license text or
  owner grant is located.
- `UNKNOWN` operations stay on the open-decision register; they may not proceed.

## 7. Machine artifact

`policies/corpus_use_policy.json` mirrors section 3 (statement/class/evidence) and
validates against `policies/policy_schema.json` (WU11).