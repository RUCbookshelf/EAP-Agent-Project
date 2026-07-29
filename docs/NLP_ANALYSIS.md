# NLP analysis v0.4

## v0.6 configuration binding

Every new coordinated AnalysisRun records the active `config-v0.6.x`. Activating or rolling back a validated
configuration updates analyzer selection and the versioned MATTR/repetition/long-sentence parameters for subsequent
runs. Existing AnalysisRuns retain their original configuration and are never silently recomputed.

Default backend: `spacy-analyzer-v0.4.0`, spaCy 3.8.7, `en_core_web_sm` 3.8.0. The model is pinned in `requirements-nlp.txt`; `run.bat` installs and checks it. Failure leaves the application runnable through an explicit, persisted BasicAnalyzer fallback.

Pipeline: raw text preservation → input-quality flags → token/sentence/lemma/POS/dependency/head/offset/noun-phrase annotations → lexical/connective/syntactic extractors → versioned MetricResults → cautious diagnosis → protected feedback prompt. Token-scale evidence is JSON artifact data, not fixed columns.

Input quality flags surface possible prefaces, editor wording, Markdown, code fences, empty/duplicate paragraphs, very short texts, title/instruction lines and metadata mismatches. They never silently remove text and never establish AI use or misconduct.

Lexical evidence includes lemma/content-word frequencies, prompt keywords, located repetition, local clustering, density, POS distribution, prototype lexical density and configurable MATTR. Prompt keywords are down-weighted unless local clustering supports a cautious review candidate. MATTR shorter than its window returns `insufficient_data`.

Connectives use `connectives-v0.4.0`, recording form, normalized form, function, sentence, paragraph and offsets. Categories are addition, contrast, cause, consequence, exemplification, sequence and conclusion. Dictionary non-detection is not absence of cohesion.

Syntactic evidence includes sentence lengths, finite-verb/subordinate/coordination/clause-like candidates, dependency depth, noun-phrase length and long-sentence candidates. Parser results are not confirmed errors, long sentences are not automatically better, and this is not T-unit or complete syntactic-complexity measurement.

Mixed Analyzer versions are never treated as silently identical. Existing v0.1 compatibility metrics remain readable; new reanalysis appends an AnalysisRun and does not call DeepSeek.
