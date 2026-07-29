# 数据模型（迁移 6）

迁移 5 在保留 `original_draft_stage` 的同时向 `essays` 追加修订元数据。`revision_groups` 保存任务内成员关系和元数据一致性；`revision_snapshots` 追加保存结构化比较、算法/资源/配置版本及限制。重算只插入新 Snapshot，不覆盖旧记录。数据库不保存 API Key。

迁移 6 新增 `configuration_versions` 与 `configuration_audit`。配置表保存白名单化 payload、状态、父版本、change note、验证结果、激活/停用时间和 SHA-256 content hash；部分唯一索引保证恰好至多一个 active。初始配置由迁移创建。旧反馈唯一约束被安全迁移为 append-only 结构，以支持明确确认的反馈再生成。API Key 仍不保存。

SQLite 默认文件为 `data/writing_feedback.db`，外键约束在每个连接上启用。v0.2 通过 Repository 协议访问数据；API 不返回原始 SQL 行或连接对象。

## 表

| 表 | 主要字段 | 用途 |
|---|---|---|
| `students` | `student_id`, `created_at`, `is_synthetic` | 匿名学习者标识；不保存姓名 |
| `essays` | `essay_id`, `student_id`, prompt, genre, draft_stage, timed, tool_use, essay_text, submitted_at | 原始作文和任务条件 |
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
