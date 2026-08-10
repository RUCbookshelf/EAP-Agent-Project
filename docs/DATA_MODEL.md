# 数据模型（迁移 14）

迁移 14（`wave2_revision_loop_and_learner_model`，Goal PDW2-A-CORE-PERSISTENCE）是 Wave-2 追加式持久化迁移：仅新建 `writing_tasks`（L2 修订循环的任务/上下文元数据）、`submission_revisions`（修订关系记录，含血缘、时间戳及任务/分析/反馈链接；现有 `revision_groups`/`revision_snapshots` 仍为分组与分析载荷的权威来源）、`learning_observations`（纵向学习观察）与 `learning_items`（学习者条目），外加索引。所有新列均有 DEFAULT 覆盖，不改动任何既有表 DDL；回滚 14→13 仅做台账式逻辑回滚（保留表与数据，重放幂等）。此前规划的 `essays.domain` 判别器车道保持未实现且触发门控，其实现 Goal 必须使用 >= 15 的版本号。

迁移 13 新增部分唯一索引 `ux_practice_targets_active_priority_key`：对每个 (student_id, source_submission_id, target_json 内 source_priority_id) 至多允许一个 ACTIVE 练习目标；无优先级引用的旧目标豁免。回滚只删除该索引，不删除数据，重建幂等。

迁移 12 新增练习与迁移证据表族：`practice_targets`、`exercise_instances`、`exercise_attempts`、`practice_evaluations`、`feedback_engagement_traces`、`within_task_response_candidates`、`transfer_evidence_candidates`、`practice_state_snapshots`，并激活 config-v0.9.0 作为 config-v0.8.2 的子版本；旧配置保留。

迁移 11 新增研究数据基础设施：`human_reviews`（人工评审）、`pii_candidates`（PII 候选）、`export_jobs`（导出任务），并激活 config-v0.8.2 作为 config-v0.8.0 的子版本。

Migration 10 additively adds nullable actual-timing fields to essays, semantic/provenance fields to metric results, append-only `analysis_units` and `error_annotations`, and active `config-v0.8.0` as a child of preserved `config-v0.7.1`. Logical rollback reactivates migration 9/config v0.7.1 without deleting additive data; re-upgrade is idempotent.

Migration 9 additively adds nullable `feedback_records.provider_status_json` and activates `config-v0.7.1` as a child of preserved `config-v0.7.0`. Existing feedback rows remain valid with no provider-status object. Logical rollback sets schema version 8 and reactivates the parent configuration while preserving the additive column, stored status JSON, essays, analyses, feedback, revisions and snapshots; re-upgrade is idempotent.

`StructuredFeedback` adds optional `longitudinal_assessment`. Submission responses additionally expose `RevisionGroupSummary`, `WithinTaskRevisionTrajectory`, and UI empty-state codes. These are derived records; they do not replace append-only Revision or Learner Profile snapshots.

Migration 8 is additive. It adds `profile_version`, `source_submission_ids_json`, and `representative_submission_ids_json` to `learner_profile_snapshots`, plus `history_evidence_registry`. The registry is append-only and stores `history_evidence_id`, student, snapshot, Task Cluster, evidence type, complete evidence JSON, registry version, and creation time.

Snapshot v2 retains old v0.3 fields for compatibility and adds source/representative/excluded IDs, Task Clusters, Data Sufficiency, Metric/Diagnostic Trajectories, current targets, strength patterns, analysis/algorithm versions, and History Evidence. Old `LP######` JSON remains readable; new v0.7 rows use `LPS######`. No historical row is updated or deleted during migration.

迁移 7 原位扩展 `metric_results`，保存 measurement status、metric confidence、reasons、risk factors、诊断/纵向准入标志和可复算 measurement metadata；旧行和旧 metric version 不覆盖。新增 append-only `diagnostic_calibrations`，保存 gate/priority/calibration 版本、完整状态集合、证据相关性、排除原因和 score components。迁移在事务中执行，失败回滚，不删除历史作文或分析。

迁移 5 在保留 `original_draft_stage` 的同时向 `essays` 追加修订元数据。`revision_groups` 保存任务内成员关系和元数据一致性；`revision_snapshots` 追加保存结构化比较、算法/资源/配置版本及限制。重算只插入新 Snapshot，不覆盖旧记录。数据库不保存 API Key。

迁移 6 新增 `configuration_versions` 与 `configuration_audit`。配置表保存白名单化 payload、状态、父版本、change note、验证结果、激活/停用时间和 SHA-256 content hash；部分唯一索引保证恰好至多一个 active。初始配置由迁移创建。旧反馈唯一约束被安全迁移为 append-only 结构，以支持明确确认的反馈再生成。API Key 仍不保存。

SQLite 默认文件为 `data/writing_feedback.db`，外键约束在每个连接上启用。v0.2 通过 Repository 协议访问数据；API 不返回原始 SQL 行或连接对象。

## 表

| 表 | 主要字段 | 用途 |
|---|---|---|
| `students` | `student_id`, `created_at`, `is_synthetic` | 匿名学习者标识；不保存姓名 |
| `essays` | `essay_id`, `student_id`, writing_prompt, genre, draft_stage, timed, time_limit_minutes, tool_use, essay_text, submitted_at, timing 字段（迁移 10）, revision 元数据（迁移 5） | 原始作文和任务条件 |
| `metrics` | `essay_id`, `metrics_json`, `analysis_version`, `limitations` | 基础表层指标 |
| `diagnoses` | `essay_id`, `diagnosis_json`, `diagnosis_version` | 优点与改进重点的结构化信号 |
| `feedback_records` | `essay_id`, `feedback_json`, provider_name, model_name, success_status, fallback_reason, prompt_version, analysis_version | 结构化反馈及生成溯源 |
| `exercises` | `essay_id`, diagnosis_category, exercise_type, exercise_json | 与诊断类别关联的练习 |
| `learner_history` | `student_id`, `essay_id`, history_summary, comparable_count | 每次提交所用的纵向摘要 |
| `system_versions` | `component`, `version`, `recorded_at` | 当前应用、分析、诊断和 prompt 版本 |
| `schema_migrations` | `version`, `name`, `applied_at` | 已应用的版本化数据库迁移 |
| `learner_profile_snapshots` | `snapshot_row_id`, `student_id`, `snapshot_json`, `analysis_version`, `configuration_version`, `included_submission_ids_json`, `created_at` | 追加式纵向 Snapshot 历史 |
| `analysis_runs` | `analysis_run_id`, `essay_id`, Analyzer/NLP/model/configuration versions, parameters/resources, fallback, duration, limitations | 每次本地分析的追加式运行记录 |
| `metric_results` | AnalysisRun, metric/version/value/unit/parameters/resources/status/evidence/limitations | 通用指标结果，不要求新增固定列 |
| `analysis_artifacts` | AnalysisRun, artifact type/schema, JSON | token、位置与词汇/衔接/句法证据 |
| `diagnostic_calibrations` | essay/AnalysisRun IDs, calibration JSON, calibration/gate/priority/configuration versions, created_at | 追加式诊断准入、排序、证据和抑制审计 |
| `human_reviews` | review_id, target_type/target_id, reviewer_id, decision, confidence, guideline_version, review_status, superseded_by, source_system_result_snapshot | 人工评审记录；更新评审通过 superseded_by 取代旧评审 |
| `pii_candidates` | pii_candidate_id, submission_id, category, offsets, matched_text, confidence, rule_id, review_status, action, reviewer_id, reviewed_at, replacement_marker | 待评审的 PII 候选 |
| `export_jobs` | export_id, filter_json, privacy_mode, formats_json, status, completed_at, export_directory, file_count, record_counts_json, excluded_counts_json, manifest_path | 研究数据导出任务（filter/privacy 白名单） |
| `practice_targets` | practice_target_id, student_id, source_submission_id, source_diagnosis_id, target_code/label, status, target_json | 练习目标；迁移 13 保证至多一个 ACTIVE 优先级键 |
| `exercise_instances` | exercise_id, practice_target_id, student_id, exercise_type, created_at, instance_json | 练习实例 |
| `exercise_attempts` | attempt_id, exercise_id, student_id, attempt_number, status, created_at, attempt_json | 练习尝试（按 attempt_number 追加） |
| `practice_evaluations` | evaluation_id, attempt_id, practice_target_id, created_at, evaluation_json | 练习评估 |
| `feedback_engagement_traces` | trace_id, student_id, target_code, created_at, trace_json | 反馈参与轨迹 |
| `within_task_response_candidates` | response_id, student_id, practice_target_id, created_at, response_json | 任务内回应候选 |
| `transfer_evidence_candidates` | transfer_evidence_id, student_id, practice_target_id, created_at, transfer_json | 迁移证据候选 |
| `practice_state_snapshots` | practice_state_snapshot_id, student_id, created_at, snapshot_json | 练习状态快照 |
| `writing_tasks` | writing_task_id, student_id, prompt, genre, task_type, modality, reference_group, timestamps, metadata/limitations | 迁移 14：Wave-2 L2 修订循环的任务/上下文元数据 |
| `submission_revisions` | revision link records with ancestry, timestamps, task-context, analysis-run and feedback-record links | 迁移 14：修订关系记录（任务/分析/反馈链接） |
| `learning_observations` | observation type, evidence refs, task/context, occurrence/recency, revision response | 迁移 14：纵向学习者观察 |
| `learning_items` | originating evidence, feedback reference, revision history, task/context, status | 迁移 14：学习者条目及状态 |

## 关系

- 一个 `student` 有多篇 `essays`。
- 每篇作文有一条 `metrics`、`diagnoses`、`feedback_records` 和 `learner_history` 记录。
- 每篇作文可有多条 `exercises`。
- `system_versions` 是组件级版本注册表，不含学生数据。

## JSON 契约

分析结果包含 8 个指标：`word_count`、`sentence_count`、`paragraph_count`、`average_sentence_length`、`unique_word_count`、`type_token_ratio`、`connective_count`、`repeated_content_words`。

诊断信号包含 `category`、`evidence`、`source_metrics`、`confidence`、`interpretation`、`limitation` 和 `kind`。`interpretation` 必须使用谨慎措辞，`kind` 区分优点与改进重点。

反馈包含 `positive_finding`、1–2 条 `priority_feedback`、至少 1 项 `exercises`、`longitudinal_comment` 和 `uncertainty_note`。Schema 由 Pydantic 在保存前验证。

## 隐私边界

数据库没有 API Key 字段。`student_id` 应使用假名标识。当前原型未提供加密、权限分级、删除/导出工作流或保留期限策略，因此不能直接用于真实学生部署。

## Repository boundary

协议分别覆盖 Student、Essay/Submission、Metric、Diagnosis、Feedback、Exercise、LearnerHistory、LearnerProfile、Configuration 和 SystemVersion。当前 SQLite 类实现这些结构契约。PostgreSQL 只是未来扩展点，尚无可用实现。

Snapshot JSON 保存比较纳入/排除记录、个人基线、指标观察与趋势、结构化问题轨迹、重点候选、置信度和限制。每次重算插入新行并获得 `LPnnnnnn`，不会覆盖旧算法版本。AnalysisRun 使用 `ARnnnnnn`；重分析只追加新运行，旧 `metrics` 表继续支持 v0.1—v0.3 查询。
