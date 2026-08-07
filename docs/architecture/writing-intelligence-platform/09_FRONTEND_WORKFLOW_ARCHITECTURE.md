# 09 — Frontend & Workflow Architecture

## 1. Principles

No visual redesign; the frozen Student design system (D1.3 tokens in `app/ui/pixel_art.py::DESIGN_TOKENS`, generated CSS, `.streamlit/config.toml` parity test) remains canonical for both domains; Streamlit stays the only runtime; the HTTP-only client boundary, stable navigation, side-effect-free reads, learner isolation, and bilingual Student UI (600/600 locale parity) are frozen contracts.

## 2. Entry model (unchanged)

Role-based (Student/Research) with per-page Student ID input; no auth/profile model (`NR`). When the Academic workspace ships, a domain-workspace selector (L2 Writing / Academic Writing) appears above the page list for the Student role; selection is session-scoped like the learner ID (persistence `NR`) (D-10). Research role remains a domain-neutral audit surface.

## 3. Mental models

- **L2 Writing — task-centric loop:** one prompt + one draft → Feedback → Revision → Practice; Journey is a timeline of task loops. Unchanged from the current product.
- **Academic Writing — project-centric hierarchy:** Paper → Sections (each a task loop: section draft → section Feedback → linked Revision → optional Practice) → Sources/evidence panel. Whole-paper feedback = separate, explicitly evidence-bound view; never a silently computed aggregate (D-12).

## 4. Shared vs domain-specific

- **Shared:** page skeleton (Home, Writing, Feedback, Practice, Revision, Journey); components (`components.py`), tokens, locale `t()`, ports, HTTP client; stable-reference navigation pattern; evidence-quote rendering; Journey event/cycle mechanics; next-action contract pattern; honest-state components (no-priority, insufficient-evidence, evaluation-unavailable, unverified).
- **Domain-specific (content and task-scope only):** L2 task metadata (task type, genre, timing, tool use); Academic paper/sections/sources surfaces.
- **Boundary rule:** shared core must not import domain feature logic; domain modules must not reimplement tokens, locale, ports, or navigation.

## 5. New shared abstractions (planned, gated on the Academic build)

1. `DomainDescriptor` registry — static, UI/workflow-scope only: `domain_id → {page map, task-form schema reference, journey stage/event config, action-contract reference, locale namespace}`. No plugin loading/hot reload.
2. `StableReferenceNav` contract — codify the existing preset pattern: presets carry only persisted references (submission_id, priority_index, practice_target_id; later paper/section IDs); destinations always validate against the current learner's persisted records; invalid refs render an honest note.
3. Domain-aware action contract — parameterize the Home/Journey state→action maps instead of adding near-copies.
4. Journey cycle configuration per domain — parameterize read-time projection; journey event vocabulary stays frozen (D-11).

## 6. Interaction contracts (both domains)

Feedback: evidence-first priority cards (max two), no-priority honesty branch, persisted-feedback-authoritative data; Revision: source-submission validation, priority selection, linked revision with bounded timeout reconciliation; Practice: priority-derived targets with provenance, create-or-reuse idempotency, one stable current exercise, explicit activity completion, evaluation-unavailable states; Journey: read-time projection, quiet semantic badges, safe action buttons; Navigation: stable references, side-effect-free.

## 7. Academic surfaces (future; no UI work in this Goal)

Paper workspace (ordered section list, version awareness, whole-paper feedback view limited to paper-scope evidence, sources panel with bound quotes); sources/evidence panel v1 = metadata + quote bindings only (no citation manager, no PDF viewer, no import pipeline); section-level task loops reuse the full existing interaction stack with `scope=section`, `parent=paper_id`.

## 8. Open decisions (explicit, unresolved)

D-1 product container (second workspace vs separate shell) — `Researcher decision required`; D-2 entry flow ordering — `NR`; D-3 persisted profile surface — `NR`; D-4 whole-paper feedback derivation — `Researcher decision required`; D-5 source model (upload vs reference-only) — `NR`; D-6 academic practice targets — `Unclear`; D-7 URL-addressable states — `Unclear`; D-8 academic journey projection — `Unclear` (recommendation: parameterized); D-9 academic task metadata schema — `NR`; D-10 workspace persistence — `NR`.

## 9. Sequencing

v0.9.7-E (responsive/mobile/accessibility) remains the next product phase; academic surfaces land after data/domain contracts (Horizon 2); all new labels pass the 600/600 locale parity test; the 1237-test core is extended, not duplicated.

## 10. Amendment (Round 4 red team)

Academic workspace carries an explicit honest state — "academic journey unavailable in MVP" — because the frozen Journey event vocabulary has no Academic event types in MVP (D-37/RT-20); the paper-anchored journey design remains in the open-decision log and is not forgotten at Horizon 2.