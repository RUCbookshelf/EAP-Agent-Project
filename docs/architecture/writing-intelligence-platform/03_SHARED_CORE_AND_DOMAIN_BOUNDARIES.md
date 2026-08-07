# 03 — Shared Core and Domain Boundaries

## 1. Principle

Shared mechanisms, domain content. Two domains are supported by real requirements before an abstraction enters the Shared Core; one verified requirement or mere similarity is not enough (YAGNI; Goal section 18).

## 2. Shared Core — stays as-is (frozen contracts, no behavior change)

Pipeline orchestration + submission workflow; repository protocols + SQLite adapters + migrations; registries (analyzer, metric, algorithm, CALF, configuration, prompt); LLM router/provider/validator/reliability; learner history + snapshot machinery; read-time Journey projection + cycle model; Revision alignment/comparability; Practice lifecycle + `PRIO-{feedback_id}-{priority_index}` provenance; locale/error/lifecycle/readiness/PII/research/export/admin services; UI shell, tokens (D1.3), components, ports, HTTP-only client; research-validity guardrails (never proficiency/mastery/learning-gain claims).

## 3. Shared Core — new mechanisms (planned, additive, no implementation in this Goal)

| Mechanism | Problem it solves | Owner | Cost now / delay |
| --- | --- | --- | --- |
| `domain`/`language` discriminator | two domains in one pipeline without mixing evidence | Shared Platform & Core | low / drift risk |
| TaskTypeRegistry (namespace-scoped) | L2 comparability defect (free-text genre + substring inference); Academic paper/section kinds stay separate | Shared mechanism; contents per domain | low / legacy-genre inference persists |
| FeedbackDimensionRegistry | honest availability states (`available | insufficient_evidence | not_applicable | research`) | Shared mechanism; contents per domain | low / silent gaps |
| FeedbackPolicy contract | gate/priority semantics today implicit in calibration constants; Domain A needs a source-verification pre-gate | Shared contract; instances per domain | low / Domain A design without a seam |
| WritingProfile contract | formalized evolution of learner snapshot v2; domain-tagged, observation-only, never-merged | Shared contract + engine; sections per domain | low / Domain A evidence sections without a seam |
| Corpus boundary contract + resource-pack descriptor | no corpus exists; makes "no authorized resource" an explicit versioned state | Shared boundary; contents per domain | low / unmanaged corpus claims |
| Epistemic-status vocabulary | observed evidence ≠ diagnostic inference ≠ feedback recommendation ≠ learning outcome; downgrade-only display | Shared | low / convention-only enforcement |
| Evidence-status vocabulary | `verified / candidate / insufficient / suppressed / not_applicable / unavailable / legacy / unresolved` | Shared | low / scattered statuses |
| Feedback audit sampling design | evaluation-of-evaluation; closes circular-evaluation gap | Shared design; operated by Research Evaluation | deferred / unmanaged quality claims |

## 4. Must NOT be promoted to Shared Core

L2 category maps, exercise catalogs, prompt wording, gate thresholds tuned for a domain, citation conventions, locale content, genre taxonomies, reference groups, construct definitions, domain entities (Source/EvidenceUnit/Claim/PaperSection/CitationLink), Academic integrity services.

## 5. Domain boundaries

### Domain B — L2 Writing Development Agent (default domain)
- Owns: non-research task types (opinion, argumentative, discussion, problem-solution, general/EAP — enumeration `Researcher decision required`); per-type expectation packs; dimension availability states; practice target-code eligibility; L2 locale labels; conservative same-type comparability rules.
- Must not own: source use, citation, register/sophistication scoring, content/task-fulfillment scoring, proficiency/CEFR/level constructs, project containers.

### Domain A — Academic Writing Agent (future module `app/academic/`)
- Owns: ResearchProject, ResearchQuestion, Source, EvidenceUnit, Claim, PaperSection, CitationLink; four provenance chains; local citation-verification service; integrity guardrails; academic FeedbackPolicy instance; academic task/paper/section kinds (separate namespace).
- Must not own: shared pipeline orchestration, registries, Journey mechanics, learner isolation, practice provenance semantics, L2 content.

## 6. Evidence-kind separation (non-negotiable)

L2 internal diagnostic evidence (draft-internal metrics/quotes feeding Feedback validation) and Academic research evidence (source-located EvidenceUnits with integrity provenance) are two different evidence kinds. They must never share a table or schema; Feedback may reference Academic evidence only by ID (D-06). Same-word traps (`evidence`, `claim`, `discourse`, `revision`, `practice`) must never be treated as shared referents without checking the underlying object and integrity obligations (Round 2 pair 1).

## 7. Abstraction verdicts (Goal section 18, 8-question test applied; full tables in `decisions.md`)

- ADOPT (constrained): WritingProfile (documentation-level now; implementation with Domain A); FeedbackPolicy (contract now; named type later); TaskTypeRegistry; FeedbackDimensionRegistry; corpus boundary contract; epistemic-status + evidence-status vocabularies; feedback audit sampling (design).
- REJECT / DEFER: AnalysisProfile (registries already cover selection); CorpusProfile as named object (no second verified requirement; boundary contract only); WorkflowProfile (highest over-generalization risk — workflow engine explicitly rejected); PracticePolicy (versioned ExerciseSpecification is the extension point); generic WritingItem super-entity; merged cross-domain WritingProfile; per-domain DBs/namespaces/protocols/clients/migrations.

## 8. Interface ownership summary

| Interface | Owner |
| --- | --- |
| API surface contract | Shared Platform & Core (freeze mechanism: `tests/contracts/api_surface_contract.py`) |
| Domain discriminator values | Shared Platform & Core (vocabulary change = shared-contract change) |
| TaskTypeRegistry / FeedbackDimensionRegistry schemas | Shared Platform & Core; contents by domain departments |
| FeedbackPolicy / WritingProfile contracts | Shared Platform & Core; instances/sections by domain departments |
| Corpus boundary contract | Corpus & NLP (with Research Evaluation governance) |
| Journey event vocabulary | Shared Platform & Core (frozen; additive via ADR) |
| Practice provenance grammar | Shared Platform & Core (frozen) |
| Locale key contract | Shared Platform & Core (additive keys only) |

## 9. Amendments (Round 4 red team)

- **Registry content layout (D-26):** domain content ships as versioned JSON/config data files under per-domain namespaces (e.g., `app/configuration/domain_packs/{domain}/{version}/...`); Python registry modules become mechanism only; registry-content tests validate each pack loads under its own namespace. This is the implementation home for "never code forks".
- **Calibration ownership (D-33):** calibration machinery and registries are shared; threshold and eligibility CONTENT lives in domain packs and changes through the shared-contract process with methodological review (AGENTS.md section 1.11). L2 calibration curve stays frozen-behavior.
- **Dimension registry axes (D-37/RT-17):** FeedbackDimensionRegistry carries two fields — `availability` (`available | insufficient_evidence | not_applicable`) and `learner_exposure` (`student | research_only`) — instead of one mixed enum.
- **Domain attribution (D-21):** `domain` is server-derived at write time from workflow/route/workspace identity; client assertion advisory only, mismatch rejected/ignored and recorded.
- **task_type semantics (D-22):** metadata-only; no comparability predicate until the legacy mapping decision; `legacy_unclassified` NULL semantics; behavior-diff test required.