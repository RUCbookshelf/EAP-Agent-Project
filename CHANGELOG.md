## v0.9.5-C (2026-08-02)

### Changed
- Extracted the six Student features and six Research features out of
  `app/ui/pages/student_pages.py` and `app/ui/pages/research_pages.py` into
  one module per visible page under `app/ui/features/student/` and
  `app/ui/features/research/`; the old page modules are now thin explicit
  re-export facades with unchanged renderer names and signatures.
- Removed the two UI-to-backend-schema boundary violations: Student Practice
  now uses the UI-safe `app/ui/contracts/practice.py` instruction contract,
  and Research Data builds its export payload with
  `app/ui/contracts/research.py` (exact backend serialization shape).
- Added a static prohibited-UI-import architecture test and extraction
  compatibility tests.

### Verified
- Contract inventory parity: renderers 13/13, definitions 32/32, API calls
  24/24, write-capable calls 7/7, session keys 6/6, widget keys 32/32,
  locale keys 98/98; zero missing/added.
- 15 new boundary/extraction tests; 200+3 focused frontend set; 24/24
  representative browser renders (en desktop + zh mobile); 446+8 core tests;
  exact `cmd /c "run.bat --verify"` PASS; migration 12; `config-v0.9.0`;
  dev database fingerprint unchanged; locale parity 520/520.
## v0.9.5-B (2026-08-02)

### Changed
- Split the centralized FastAPI business-route registration into feature-owned
  router modules under `app/api/routers/` (system, submissions, analysis,
  students, revisions, practice, journey, research, calf, admin); `app/api/main.py`
  is now an application composition root.
- `/api/v1/system/health` now has exactly one canonical lifecycle-based handler
  with identical production/test semantics; the duplicate business health handler
  and the unreachable duplicate lifecycle-route block in `create_app` were removed.
- Production and test builders now populate the same lifecycle analyzer/NLP
  facts, fixing production health reporting of the spaCy model.

### Verified
- Route inventory parity: 77 unique path+method pairs before and after; zero
  missing/added endpoints; no duplicate path+method; operation IDs unchanged.
- 274 passed + 3 skipped focused API tests; 431 passed + 8 skipped core tests
  (+10 new contract tests); minimal runtime smoke PASS; exact
  `cmd /c "run.bat --verify"` PASS; migration 12; `config-v0.9.0`.
## v0.9.4-B (2026-08-01)

### Added
- Shared Student presentation primitives for page purpose, task steps, learner
  context, and one clearly ranked action.
- Focused verification for all six Student pages and one isolated cross-page
  write flow; 520/520 English/Chinese locale parity.

### Changed
- Redesigned Home, Writing, Feedback, Practice, Revision, and Learning Journey
  around learner context, current task, evidence, next action, and explicit
  limits. Student content width is 720px with mobile control stacking and
  44px touch targets.
- Accessible focus token updated to 3px `#0f6dbd` (5.33:1 on white, 4.84:1
  on the surface, 3.16:1 on the dark boundary).
- Legacy v0.9.2.1 Playwright isolation now respects `DATABASE_PATH` and the
  current focus-token contract.

### Verified
- 95 passed + 1 skipped affected tests; 130 passed + 2 skipped Student
  regression; 421 passed + 8 skipped core tests.
- Controlled cross-page flow PASS; 24/24 required Student renders; 6/6
  required Research smoke renders; legacy Playwright PASS; lifecycle and
  exact `cmd /c "run.bat --verify"` PASS.
- Migration 12, `config-v0.9.0`, Research IA, API/schema/domain contracts, and
  read-time Journey semantics unchanged.

## v0.9.4-A (2026-08-01)

### Added
- Hybrid Pixel System 2.0 foundation: canonical `DESIGN_TOKENS` in
  `app/ui/pixel_art.py` with generated CSS; Streamlit theme
  (`.streamlit/config.toml`) aligned via parity tests.
- Readable local/system sans body stack; monospace constrained to
  technical/brand roles; shared spacing, geometry, focus, semantic status,
  density, and responsive tokens.
- Local accessible SVG icon primitive (`app/ui/pixel_art.py::icon`).
- Shared primitives in `app/ui/components.py`: `field_error`, `loading_box`,
  `data_table`, `technical_caption`, `validate_writing_form`; stable
  `data-testid` attributes on existing notices/badges/empty states.
- 80 new tests (`tests/test_design_tokens_v094a.py`,
  `tests/test_hybrid_components_v094a.py`) and
  `scripts/design_system_audit_v094a.py`.

### Changed
- Primary action red `#ff004d` → `#e00047` (measured 4.93:1 white-on-red for
  normal/hover/active); `#ff004d` retained as decorative non-text accent.
- Writing page blocks empty Writing prompts with a localized field error
  before the API call (server validation and payloads unchanged).
- Research Data: "Target ID" and "Export:" success prefix routed through
  locale keys; Run Export shows a loading state; Learning Process Journey
  counts render as a compact table.
- Repaired: `render_research_overview` undefined `exc`; CSS selectors
  updated for the Streamlit 1.60 DOM (buttons carry `data-testid`, tabs are
  `[role="tab"]`, radios use `stRadioGroup`).

### Verified
- 394 passed, 8 skipped (core, excluding live); live A–G 20 passed; legacy
  Playwright suites PASS; lifecycle PASS; `run.bat --verify` PASS; focused
  zh-navigation probe 3/3; representative suite 24/24; final acceptance
  matrix 48/48 renders.
- Migration 12 and config-v0.9.0 unchanged.

## v0.9.3-C (2026-08-01)

### Fixed
- UX-001: Learning Journey no longer appears permanently empty. Journey
  events are derived at read time from authoritative source records
  (app/journey/service.py); every event maps to a real record and no event is
  created by page rendering, navigation, locale switching, or refresh.
- DATA-001: empty-state messages are now accurate per missing record type
  (learner not found, no submissions, no analysis, gate-suppressed priority,
  no practice target, no attempt, no evaluation, no revision, no response
  observation); errors are never shown as empty states.
- UX-003: Student ID is normalized and shared across Student pages; switching
  learners clears learner-scoped state.
- ERR-003: Journey/Practice fetches show a loading state.
- Practice Evaluation flow was unwired (service/repository existed, no API/UI
  caller); valid attempts are now evaluated with the existing conservative
  rule-based evaluator and persisted.

### Added
- Journey event semantic contract with stable types, source traceability,
  deduplication keys, event versioning, and conservative limitations.
- GET /api/v1/students/{student_id}/journey; read-only practice endpoints
  (exercises by target, attempts by exercise).
- Deterministic demo journey: `python scripts/demo_journey.py
  --setup|--status|--cleanup` for synthetic learner DEMO-001 (idempotent,
  scoped cleanup, local provider only, DB backup before setup).
- 28 journey tests (tests/test_journey_v093c.py).

### Changed
- Student Home derives latest status/next action from the journey endpoint
  (replaces the empty engagement-trace dependency).
- Research Learning Process shows the journey trace with source IDs.
- Locale keys: 368 en/zh_CN parity (journey + practice states).

### Notes
- No schema change; migration stays 12; config-v0.9.0 unchanged.
- FeedbackEngagementTrace retained but not written by the journey; page
  display is never engagement.
- No mastery/learning-gain/causal/transfer/proficiency/CEFR claim is created.

## v0.9.3-B (2026-07-31)

### Fixed
- ERR-001: all eight broken Research endpoints repaired. Missing service
  methods (apply_pii_review), missing repository persistence (save_human_review,
  list_human_reviews), route ordering (export/history shadowed by /{export_id}),
  and missing routes (dataset-split, export manifest) restored.
- ERR-002: generic API-unavailable mapping replaced by a canonical error
  taxonomy (app/errors.py) with 14 stable categories, message keys, HTTP
  statuses, and retryability flags.
- PERF-001: centralized timeout profiles (connect 2s, read 10s, write 30s,
  long-read 60s, lifecycle 5s); no unclassified long wait remains.
- Request correlation: X-Request-ID generated/propagated, added to response
  headers and canonical error bodies, and logged in sanitized request lines.

### Added
- Canonical error model app/errors.py (ApiError, ErrorCategory).
- Server-side exception mapping (validation, not-found, conflict, privacy,
  degraded, internal) with request IDs.
- Client-side classification (connect/read timeout, refused, interrupted,
  4xx/5xx, malformed response) in app/ui/api_client.py.
- Bounded safe retry: GET-only, at most 1 retry, retryable categories only;
  state-changing writes never auto-retried.
- Role-appropriate error presentation (render_api_error): Student plain
  language + Retry only when safe; Research shows category/operation/request
  ID/status/retryable/detail.
- 24 new locale keys (en + zh_CN; 295 keys each, parity preserved).
- Research Data: export history, manifest, status, dataset split, PII review,
  human review persistence all working through real HTTP.
- 25 new tests in tests/test_request_reliability_v093b.py.
- TestLiveG_MobileViewport updated to the v0.9.1+ role-based navigation.

### Backend
- Migration 12 preserved; config-v0.9.0 preserved.
- No CALF/diagnosis/practice/learner-model/privacy/dataset-split semantics changed.
- pytest: 314 passed, 8 skipped; Cases A-R: 110 passed.

## v0.9.3-A (2026-07-31)

### Fixed
- REL-001: Intermittent FastAPI startup hang eliminated. Heavy initialization
  (spaCy, database, services) moved from module-level import to FastAPI lifespan
  context manager. Server now responds to liveness checks immediately.
- API client timeout reduced from 90s to 15s for faster failure detection.

### Added
- Service lifecycle model (app/lifecycle.py): ServiceState enum, ServiceLifecycle
  thread-safe singleton with stage timing and sanitized health info.
- Liveness endpoint: GET /api/v1/system/live -- confirms process is alive.
- Readiness endpoint: GET /api/v1/system/ready -- confirms all required deps available.
- Stale process cleanup in run_local.py (kill_port_processes).
- Lifecycle-aware Streamlit UI: distinguishes API starting from unavailable.
- New locale keys: app_api_starting, app_api_failed (en + zh_CN).

### Changed
- app/api/main.py: create_app() uses FastAPI lifespan for production mode.
  Backward-compatible with tests via optional settings/repository parameters.
- scripts/run_local.py: bounded readiness polling with 60s deadline.
- scripts/service_processes.py: added kill_port_processes().
- app/ui/api_client.py: timeout 90s -> 15s; added live(), ready(), lifecycle_state().
- Health endpoint enhanced with lifecycle_state and startup_elapsed_ms.

### Backend
- Migration 12 preserved. Active configuration config-v0.9.0 preserved.
- All existing backend behavior unchanged after readiness is reached.
- pytest: 289 passed, 8 skipped (baseline: 271 passed, 8 skipped).
﻿
## v0.9.2.1 (2026-07-31)

### Added
- Playwright 1.61.0 + Chromium 149 browser testing dependency
- Comprehensive v0.9.2.1 Playwright verification suite (4 locale/viewport
  combos, 12 pages, console/overflow/focus/styles/role-separation/screenshots)
- Static Pixel Art style audit script (scripts/pixel_art_style_audit.py)
- Pixel Art design system reference (docs/design/PIXEL_ART_DESIGN_SYSTEM.md)
- v0.9.2.1 specification (docs/development/V0.9.2.1_SPEC.md)
- 13 deterministic screenshots at verification/screenshots/v0.9.2.1/

### Fixed
- Role-separation: global header no longer exposes analyzer version and
  provider details to Student View
- Navigation: sidebar page labels fully localized (en + zh_CN) via locale
  system; no English leakage in Chinese mode
- Decorative single-side accent borders (.px-notice-limitation, .px-quote)
  changed to full 4px borders per design rules

### Verification
- Playwright: 4 locale/viewport combos (EN desktop, ZH desktop,
  EN mobile 390x844, ZH mobile 390x844), all 12 pages PASS
- Console errors: 0; page exceptions: 0; horizontal overflow: none
- Focus: visible blue outline (rgb(41,173,255) solid 3px, offset 2px)
- Role separation: PASS (no prohibited content in Student View)
- Static style audit: 0 violations
- Computed-style audit: all zero radius, no gradients/blur/soft shadows,
  zero transitions, no animations
- Rerun idempotency: no duplicate exercise instances
- pytest: 271 passed, 8 skipped; Cases A-R: 110 passed
- run.bat --verify: PASS (migration 12, config-v0.9.0, all HTTP 200)
- Security: no tracked credentials; .env gitignored; clean screenshots
- Backend: no changes (migration 12, config-v0.9.0 preserved)

### Backend
- No changes to migration 12, config-v0.9.0, or any backend code
## v0.9.2 (2026-07-31)

### Changed
- Complete Pixel Art UI redesign with centralized CSS token system
- Square corners, hard offset shadows (2px/4px/8px), solid colors, no gradients
- Canonical 7-color palette: #1a1c2c, #ffffff, #f4f4f4, #ff004d, #00e436, #29adff, #ffec27
- Monospace typography stack (ui-monospace, Cascadia, Consolas, SFMono, Menlo, etc.)
- All transitions set to none; immediate hard state changes for hover/active/focus
- Reusable component library redesigned: page_header, section_header, metric_card,
  feedback_priority_card, timeline_event, status_badge, notices (warning/error/
  success/info/limitation), empty_state, audit_record, table_container, divider
- Global application shell with pixel-art sidebar, borders, and typography
- All 12 pages (6 Student + 6 Research) redesigned with pixel-art cards and layouts
- Streamlit form controls restyled: square corners, thick borders, blue focus outlines
- Responsive: smaller borders and shadow offsets on mobile (<=640px)
- prefers-reduced-motion: explicit animation/transition disable
- Nested cards eliminated; replaced with flat sections, separators, and rows

### Backend
- No changes to migration 12, config-v0.9.0, or any backend code
- 271 pytest passed, 8 skipped (unchanged from v0.9.1 baseline)

### Design references
- Token files archived at docs/design/reference/pixel-art/
## v0.9.1 (2026-07-31)

### Added
- Role-based navigation: Student View (6 pages) and Research View (6 pages)
- Reusable UI component system (status_badge, metric_card, evidence_quote, etc.)
- Progressive disclosure rules hiding internal IDs from Student View
- Visual design system with responsive CSS (desktop to 390x844 mobile)
- 61 new i18n keys (271 total, en + zh_CN parity)
- Expanded Playwright tests (6 scenarios: desktop, research, mobile, Chinese, keys, home)

### Changed
- Complete Streamlit UI rewrite with modular page architecture
- Sidebar navigation: language switcher, role selector, page navigation
- Student Home page with task summary, status, and next-action recommendations
- Student Writing page with grouped field sections
- Student Feedback page with strengths, max 2 priorities, evidence, next step
- Student Revision page with draft chain, changes, priorities, uptake
- Student Learning Journey with chronological timeline events
- Research Overview with system status and data quality
- Research Evidence with submission/analysis/diagnosis audit
- Research CALF Measures with grouped metric cards
- Research Learning Process with complete evidence chain
- Research Data with 8 organized subsections
- Research System Audit with diagnostic, learner model, reanalysis, admin

### Fixed
- All UI strings now routed through locale system
- No raw locale keys appear in user-facing text
- BOM stripped from all new source files

### Backend
- No changes to migration 12, config-v0.9.0, or any backend code


# Changelog

## 0.9.0 — 2026-07-30
- Added Practice Target, Exercise Instance, Exercise Attempt, Practice Evaluation, Feedback Engagement Trace, Within-task Response Candidate, and Transfer Evidence Candidate infrastructure with migration 12 and config-v0.9.0.
- Implemented deterministic exercise generation with three exercise types and conservative rule-based evaluation without mastery/scoring language.
- Added Streamlit Practice, Learning Journey, and Practice Audit pages with sidebar navigation.
- Added 20-case Live A-G controlled validation suite and desktop/mobile Playwright verification (1280×900 and 390×844).
- Added 210 locale keys in en and zh_CN for all practice UI text.
- All practice records are append-only with generated IDs; DeepSeek practice generation disabled by default.
- No mastery, proficiency, CEFR, scoring, or causal claims introduced.


## 0.8.1 — 2026-07-30
- Added English/Simplified Chinese multilingual UI with locale files in `locales/`; all user-facing labels, status descriptions, and metric explanations are internationalized.
- Refactored CALF display with classified metric cards showing construct grouping, unified status labels (Research metric/Descriptive proxy/Automatic candidate/Unavailable), confidence, analysis unit, and version per measure.
- Reorganized result tabs by view mode with role-based information isolation; student view hides technical metadata.
- Added sidebar language picker supporting runtime switching without restart.
- No new measurements, scoring, CEFR, or v0.9 functionality introduced.

## 0.8.0 — 2026-07-30
- Added versioned CALF construct, measurement-specification, and analysis-unit registries; deterministic MTLD/HD-D; research-only syntactic candidates; append-only error annotations; and actual-duration-only writing output rate.
- Added migration 10, `config-v0.8.0`, CALF APIs/research UI, Cases A–M, opt-in live A–D verification, and explicit prompt/diagnosis/longitudinal isolation.
- Accuracy, lexical sophistication, validated clause/T-unit measures, CALF totals, writing scores, ability/proficiency/CEFR claims, and v0.9 remain unavailable or out of scope.

## 0.7.1 — 2026-07-30

- Added backend-owned `longitudinal_assessment`, conservative field-level repair, positive-finding ability-inference guardrails, and auditable provider execution status.
- Added migration 9 and `config-v0.7.1` without deleting historical data; logical rollback reactivates `config-v0.7.0`.
- Added within-task revision trajectory, first-to-latest and pairwise comparisons, explained empty-state codes, and backward-compatible API fields.
- Refined Streamlit into Feedback, Revision, Progress, Evidence, and Research Audit tabs with Student/Research audit modes and explicit independent-task/revision entry.
- Added Cases 1–10 regression coverage, live DeepSeek A–C verification, and desktop/mobile Playwright QA. No v0.8, scoring, CEFR, model training, cloud deployment, or frontend rewrite was introduced.

## 0.7.0 — 2026-07-30

- Added immutable Learner Profile Snapshot v2, task clustering, four revision representative strategies, explicit Data Sufficiency, version-separated Metric/Diagnostic Trajectory v2, current learning targets, strength patterns, and append-only History Evidence.
- Added migration 8 and active `config-v0.7.0` as a child of preserved `config-v0.6.2`; historical essays, analysis runs, diagnoses, revisions and snapshots remain readable.
- Added screened `feedback-prompt-v0.7.0`, Learner Model APIs/UI, Case A–I fixtures, and an opt-in three-task live DeepSeek test.
- No CALF/CEFR/overall score, causal learning claim, cloud deployment, paid embedding service, or v0.8 feature was added.

## 0.6.1 — 2026-07-29

- Added versioned Metric Confidence with reproducible lexical measurement metadata.
- Added an append-only Diagnostic Gate, transparent Priority Score, and evidence-relevance validation.
- Calibrated distributed lexical repetition, necessary task terms, and connective-location requirements.
- Separated verified strengths from descriptive signals and calibrated parser-candidate names/counts.
- Restricted FeedbackContext and exercise generation to evidence-verified selected priorities; zero priorities are valid.
- Added migration 7, active `config-v0.6.2`, researcher audit API/UI, fixed first/revised-draft fixtures, and live DeepSeek verification.
- Preserved the one-retry/3,600-token correction path, exact quotations, redaction, Pydantic validation, and LocalDemo fallback.

## Unreleased fixes

- Fixed the timed-writing form so the time limit can be edited before submission; the value is persisted only for timed writing.
- Made DeepSeek schema failures actionable without recording response content or secrets.
- Corrected the retry instruction so invalid evidence quotations are replaced with exact essay substrings.
- Doubled the output budget only for the single correction attempt, preventing complete structured feedback from being truncated while retaining the configured first-call budget.
- Added visible provider configuration and sanitized fallback diagnostics to the Streamlit page.

## 0.6.0 — 2026-07-29

- Added API-sourced student timelines, issue trajectories, comparability summaries and version-separated metric series.
- Added dedicated Streamlit progress, revision-comparison and local-researcher administration pages.
- Added append-only non-sensitive configuration versions with validation, activation, rollback, content hashes and audit records.
- Added Analyzer, Metric, Algorithm, Prompt and Configuration registries and comprehensive version transparency.
- Added scoped reanalysis preview/run for submission, revision group, student and AnalysisRun; local-only by default.
- Removed the legacy one-feedback-per-essay constraint so explicitly confirmed LLM regeneration is append-only.
- Added migration 6 and CALF extension seams without any CALF total or proficiency field.

## 0.5.0 — 2026-07-29

- Added explicit Revision Groups and validated first/revised/final draft chains.
- Added deterministic paragraph, sentence and token alignment with major-rewrite detection.
- Added observed metric changes, diagnosis trajectories and non-causal feedback-uptake candidates.
- Added append-only Revision Snapshots, revision APIs and a Streamlit revision workflow.
- Default longitudinal trends use one representative draft per Revision Group: final, otherwise latest.
- Added Prompt/Schema v0.5 evidence-ID validation and explicit exercise-source metadata.

## 0.4.0 — 2026-07-29

- 新增可注册的 `SpacyAnalyzer` 与显式 `BasicAnalyzer` 回退，固定 spaCy 3.8.7 / en_core_web_sm 3.8.0。
- 新增输入质量提醒、词元和内容词分析、题目关键词降权、MATTR、lexical density、连接表达位置/功能分类及原型句法候选。
- 数据库迁移 4 新增 append-only AnalysisRun、MetricResult 与分析 Artifact；单篇重分析不覆盖旧结果且默认不调用 LLM。
- Prompt v0.4 仅向 Provider 暴露结构化 NLP 证据，并继续执行 Pydantic、诊断 ID、历史 ID 和逐字引文验证。
- health/API/Streamlit/run.bat 同步显示 NLP 资源、活动 Analyzer 和显式回退状态。

## 0.1.0 — 2026-07-29

- 建立分层 Streamlit、SQLite、Pydantic MVP。
- 实现基础 Analyzer 和谨慎的启发式 Diagnosis。
- 实现 DeepSeekProvider、LocalDemoProvider 与自动回退。
- 实现三类诊断关联练习。
- 实现历史读取、可比性检查和纵向描述。
- 加入 3 名虚拟学生、9 篇作文和完整闭环验证脚本。
- 加入 12 项 pytest 测试、实际 Streamlit HTTP 启动测试和项目文档。
- 新增新电脑安装指南与 Windows 一键安装/启动脚本。
- 扩大 Git 忽略规则，排除虚拟环境、密钥文件、Python 缓存和全部 SQLite 数据库。
- 使用全新的临时 Python 3.11 环境完成从零安装与启动验证。

## 0.1.1 — 2026-07-29

- 模块化并固化 Prompt 模板、版本、SHA-256 manifest 和 fail-closed 漂移检查。
- 为诊断与历史证据增加稳定 ID，并严格验证反馈引用、逐字作文证据、练习关联和无历史措辞。
- 增加 DeepSeek 一次纠错重试、LocalDemo 自动回退和逐次调用审计；无效主模型输出不会保存为正式反馈。
- 完成同一虚拟学生两次真实 DeepSeek 提交：第二次请求包含 2 条历史证据并返回有效 `H001`、`H002`，无重试、无回退。
- 普通测试最终结果为 42 passed、1 个默认跳过的可选 live test；`run.bat --verify` 返回 Streamlit HTTP 200。

## 0.2.0 — 2026-07-29

- 增加 FastAPI v1 统一后端，提供健康、版本、提交、学生、历史、profile 和 progress 接口。
- 将 Streamlit 改为纯 HTTP API 客户端，不再构造业务服务或访问 SQLite、Analyzer、Diagnoser、Prompt、Provider。
- 增加框架无关的 `SubmissionService`、命名 Repository 协议和 SQLite 实现扩展点。
- 引入 `PRAGMA user_version` + `schema_migrations` 的可重复非破坏迁移；支持空库、v0.1.1 旧库和重复升级。
- `run.bat` 现会迁移数据库、启动 FastAPI、轮询 health，再启动 Streamlit；`--verify` 同时探测 health、`/docs` 与 Streamlit。
- 保留 v0.1.1 Prompt、证据 ID、引文校验、Pydantic、重试和回退链路。

## 0.3.0 — 2026-07-29

- 增加版本化 ComparabilityResult、BaselineProfile、MetricTrend、IssueTrajectory、PriorityCandidate 和 LearnerProfileSnapshot。
- 增加可解释的可比较性、个人描述性基线、线性趋势、相对变化、波动性和保守置信度规则。
- 使用结构化诊断追踪 persistent、recurring、inconsistent、recently_reduced 和 insufficient_evidence。
- 数据库迁移 3 新增 append-only `learner_profile_snapshots`；重算不覆盖旧 Snapshot。
- progress/profile API 返回真实 v0.3 结构，并支持 metric、日期、comparable_only 和 analysis_version 查询。
- Prompt 升级至 `feedback-prompt-v0.3.0`；只发送筛选后的 Snapshot，纵向评论仍必须绑定经验证的 H 证据 ID。
- 增加四类纯虚拟纵向场景和完整回归/纵向/API/持久化测试。


