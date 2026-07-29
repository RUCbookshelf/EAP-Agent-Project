# Task Clustering v0.7

Task Clusters prevent unlike work from being silently pooled. The deterministic key includes genre, inferred writing purpose, timed/untimed state, time-limit band, tool-use class, independent/revision mode, conservative prompt family, analyzer family and metric-version signature.

Default Revision Group policy is `final_or_latest`: use the last final draft when present, otherwise the latest draft. Alternatives are `first_draft_only`, `latest_draft_only`, and `all_drafts_research_mode`. All drafts remain in the revision subsystem regardless of representative selection.

Each cluster records member and representative IDs, exclusions, rule version, comparability label, confidence and limitations. Matching metadata does not establish semantic or psychometric equivalence. Genre, tool class and analyzer/version differences split clusters by default.
