# Reanalysis v0.6

The admin workflow supports a submission, Revision Group, student or existing AnalysisRun as scope. Preview resolves
the exact submission IDs, Analyzer, configuration, count, append-only behavior and LLM-cost state before execution.

Run creates a new AnalysisRun for every target. Revision-group members also produce new Revision Snapshots while old
Snapshots remain. The default path is local Analyzer only and sets `llm_called=false`. LLM feedback regeneration
requires both `call_llm=true` and `confirm_llm_cost=true`; it appends a feedback record and can incur provider charges.
It never creates a replacement essay or overwrites an earlier feedback record.

Reanalysis is evidence for algorithm/configuration comparison, not retrospective educational validation. Version
incompatibility remains visible.
