# 项目状态

## Current v0.9 State

- Status: \completed\; database migration 12; active configuration \config-v0.9.0\, parent \config-v0.8.2\ preserved.
- 8 practice tables: targets, instances, attempts, evaluations, engagement traces, within-task responses, transfer evidence candidates, state snapshots.
- Deterministic exercise generation (3 types), conservative rule-based evaluation, no mastery/scoring/CEFR/causal language.
- Streamlit Practice, Learning Journey, and Practice Audit pages.
- 210 locale keys (en + zh_CN), identical sets.
- Live A-G validation: 20 tests pass. Playwright: desktop + 390x844 mobile pass with no console errors.
- Smoke stack: FastAPI/docs/Streamlit HTTP 200. Full regression: 269 passed, 5 skipped.
- DeepSeek practice generation disabled by default; deterministic fallback verified.
- All practice records append-only. No model training. No cloud deployment.

v1.0 remains ot_started\.

## 当前 v0.9 状态

- 状态：\completed\；数据库迁移 12；active configuration \config-v0.9.0\，父版本 \config-v0.8.2\ 保留。
- 8 个练习数据表。确定性练习生成（3 种类型），保守的规则评估，无掌握/评分/CEFR/因果语言。
- Streamlit 练习、学习旅程、练习审计页面。
- 210 个本地化键值（en + zh_CN），完全匹配。
- Live A-G 验证：20 项测试通过。Playwright：桌面和 390x844 移动端通过，无控制台错误。
- Smoke stack：FastAPI/docs/Streamlit HTTP 200。全量回归：269 通过，5 跳过。
- DeepSeek 练习生成默认关闭；确定性回退已验证。
- 所有练习记录仅追加。无模型训练。无云部署。

v1.0 保持 ot_started\。

## 当前 v0.8.1 状态
- 状态：`completed`；应用 0.8.1；数据库迁移 10；active configuration `config-v0.8.0`，父版本 `config-v0.7.1` 保留。
- 新增多语言界面（en/zh_CN）、CALF 指标分类卡片、角色视图隔离、侧栏语言切换器。
- 无新增测量能力、评分、CEFR 或 v0.9 功能。

## 当前 v0.8 状态
- 状态：`completed`；应用 0.8.0；数据库迁移 10；active configuration `config-v0.8.0`，父版本 `config-v0.7.1` 保留。
- 4 个 CALF 构念、22 个测量规范、14 个分析单位已注册；MTLD/HD-D 与真实时长 WPM 已实现，句法仅候选，Accuracy/lexical sophistication 不可用。
- 无 CALF 总分、作文评分、能力/熟练度/CEFR 推断；v0.9 保持 `not_started`。

## 当前 v0.7.1 状态

- 状态：`completed`；应用 0.7.1；数据库迁移 9；active configuration `config-v0.7.1`，父版本 `config-v0.7.0` 保留。
- Prompt/Schema 为 `feedback-prompt-v0.7.1` / `structured-feedback-v0.7.1`。纵向事实由后端生成；DeepSeek只能在结构化边界内表述，局部不可靠文字可被服务端修复。
- 同一 Revision Group 的多稿只贡献一个跨任务代表项，同时通过 Within-task Revision Trajectory 显示 Draft Chain、逐稿比较及第一稿到当前稿。
- Streamlit 使用五个结果 Tab 和学生/研究者视图；UI重渲染读取 session/API 结果，不再次调用分析器、LLM 或创建 Snapshot。
- 验收：209 passed、4 个显式 live 测试默认 skipped；DeepSeek Live A–C 通过且全部 fallback false；`run.bat --verify` 与 FastAPI/docs/Streamlit HTTP 200 通过。
- v0.8 与所有能力评分、CEFR、CALF 总分、云部署和前端框架替换仍为 `not_started`。

## v0.7 retained baseline

- 状态：`completed`；应用 0.7.0；数据库迁移 8；active configuration `config-v0.7.0`，父版本 `config-v0.6.2` 保留。
- Snapshot v2 为 `learner-profile-v0.7.0`；Task Cluster、Data Sufficiency、Metric/Diagnostic Trajectory、Learning Target、Strength Pattern 与 History Evidence 独立版本化。
- 默认代表稿策略为 `final_or_latest`；另支持 `first_draft_only`、`latest_draft_only` 和 `all_drafts_research_mode`。
- 两个任务只允许成对描述；三个任务才允许临时方向；五个任务才达到 adequate descriptive trend。它们都不是能力或学习增长判断。
- 当前 Diagnostic Gate 始终优先，允许零当前学习目标。
- v0.8、CALF、T-unit、CEFR、总分、云端与微信小程序均保持 `not_started`。

## 当前 v0.6.1 状态

- 状态：`completed`；应用 0.6.1；数据库迁移 7；active configuration `config-v0.6.2`。
- Analyzer、Diagnosis、Diagnostic Gate、Priority、Prompt 与 StructuredFeedback 均记录 v0.6.1 版本。
- Metric Confidence、可复算词汇口径、raw/monitored/selected 分离、证据相关性验证、保守练习上限和研究者审计视图均可用。
- First Draft 与绑定 Revised Draft 回归通过；分散出现 3 次且无局部聚集的 `bias` 保持 monitored，不进入学生优先反馈。
- 真实 DeepSeek First Draft：provider `deepseek`，model `deepseek-v4-flash`，validation `passed`，retry 0，fallback false。
- 完整测试：183 passed，2 skipped；FastAPI、API docs、Streamlit 均 HTTP 200；`run.bat --verify` PASS。
- At the earlier v0.6.1 checkpoint, v0.7 and CALF were `not_started`; v0.7 is now completed and CALF remains outside scope. All thresholds remain educationally and psychometrically unvalidated prototype parameters.

## 当前 v0.6 状态

- 应用 0.6.0；数据库迁移 6；active configuration `config-v0.6.1`（可版本化管理）。
- 进展、修订和管理视图均只通过 FastAPI 获取结构化结果，Streamlit 不重算研究指标。
- 配置 payload 只允许 Pydantic 白名单中的非敏感字段；Key、密码和完整敏感环境变量不进入数据库/API/UI。
- 重分析默认仅运行本地 Analyzer；LLM 再生成必须单独勾选并确认可能费用。
- Historical v0.6 checkpoint: v0.7/CALF measurement was then not started; v0.7 is now completed while CALF remains not started.

## 当前 v0.5 状态

- 应用 0.5.0；数据库迁移 5；修订 Prompt/Schema 0.5.0。
- 已实现显式修订链、本地对齐、Revision Snapshot、API 与 Streamlit 工作流。
- 修订证据与跨任务纵向证据分离；长期趋势默认对同一修订组去重。
- 2026-07-29 真实 DeepSeek 纵向与 v0.5 修订证据调用均通过且未回退；修订反馈引用有效 R001–R005，报告未记录 Key 或敏感请求。
- 所有规则仍是 prototype heuristics，须由教师/研究者审核。

## v0.1 基线（升级前）

记录时间：2026-07-29。

- 应用版本：0.1.0；Prompt：`feedback-prompt-v0.1`；诊断：`prototype-diagnosis-v0.1`。
- 现有测试：12 collected，12 passed（1.27 秒）。
- Streamlit：端口 8523 返回 HTTP 200。
- 原 `run.bat --install-only`：成功复用 Python 3.11.15 `.venv` 并核对依赖。
- 原 DeepSeek 请求只发送 essay、metrics、diagnosis、自然语言 history summary 和 Schema；System Prompt 与请求拼接混在 Provider 中。
- 原输出没有 diagnosis_id、history_evidence_id、逐字引文验证、纠错重试或逐次调用审计。
- 升级开始时项目 `.env` 不存在，进程也没有 DeepSeek Key/Base URL/Model 环境变量。

## 当前 v0.1.1 状态

- 应用、诊断、Prompt 和反馈 Schema 已升级为 v0.1.1。
- Prompt 模板、构造器和版本/哈希逻辑已模块化。
- 完整写作任务、结构化指标、诊断和历史证据进入最终 DeepSeek messages。
- 所有改进反馈和练习必须绑定有效 diagnosis_id；所有作文引文必须是规范化空白后仍逐字存在的子串。
- 纵向评论必须绑定有效 history_evidence_id；无证据时必须明确无法判断且不得产生确定性发展结论。
- DeepSeek 输出失败可纠错重试一次；第二次失败后才保存 LocalDemo 正式反馈。
- SQLite 可原位迁移 v0.1 Schema，并新增逐次 `llm_call_records`。
- 普通测试：42 passed，1 live test skipped（live 测试默认不访问外部 API）。
- 新版 `run.bat`：现有 `.venv`、全新 `.venv`、无 `.env`、临时 `.env`、缺失数据库、Prompt 模板和 HTTP 启动均已验证。

## 真实 DeepSeek 状态

状态：`PASS`。

2026-07-29 使用项目 `.env` 完成同一虚拟学生的两次真实 DeepSeek 提交。两次正式反馈均由 `deepseek` / `deepseek-v4-flash` 返回；第二次请求包含 2 条结构化历史证据，返回并通过 allowlist 验证的 ID 为 `H001`、`H002`。后置验证状态为 `passed`，`retry_count=0`，`fallback=false`。

验证结果已保存到 `data/live_deepseek_verification.json` 和 `data/live_deepseek_verification.db`，并由 `scripts.audit_live_verification` 独立复核为 `PASS`。报告、审计表结构和正式反馈记录均不包含 API Key；先前的 `data/live_deepseek_verification_blocker.json` 仅作为配置完成前的历史记录保留，已被本次成功验证取代。

逐项证据状态见 `docs/V0_1_1_COMPLETION_AUDIT.md`。

## v0.2 current state

- FastAPI v1 is the unified local backend; Streamlit is an HTTP-only client.
- Framework-neutral `SubmissionService` retains the v0.1.1 protected feedback path.
- Named Repository protocols isolate the SQLite adapter.
- Database migration version is 2 and preserves existing records.
- Health, `/docs`, submission, retrieval, student, history, placeholder profile and placeholder progress APIs are implemented.
- LocalDemo, no-environment-file, actual dual-service startup and Streamlit-through-API submission have passed.
- Cloud deployment, PostgreSQL and WeChat are not implemented or claimed.

## v0.3 current state

- Application version 0.3.0; API v1; database migration 3.
- Longitudinal analysis version `longitudinal-v0.3.0`; configuration `longitudinal-config-v0.3.0`; comparability rules `comparability-v0.3.0`.
- Prompt version `feedback-prompt-v0.3.0`; StructuredFeedback Schema remains `structured-feedback-v0.1.1`.
- Comparability, baseline, metric trends, variability, conservative confidence, issue trajectories, priorities and append-only Snapshots are implemented.
- progress/profile APIs are active; no CEFR, overall score, ranking or validated ability-change output exists.
- v0.4 remains not_started and is outside the current authorization.

## v0.4 historical state

- Historical note: authorization at that checkpoint covered v0.4 → v0.5 → v0.6 only; later v0.7/v0.7.1 authorization is recorded above.
- Application 0.4.0; migration 4; `spacy-analyzer-v0.4.0`; `prototype-diagnosis-v0.4.0`; `feedback-prompt-v0.4.0`.
- spaCy 3.8.7 and en_core_web_sm 3.8.0 are pinned; model failure is visible and falls back to BasicAnalyzer.
- AnalysisRun, MetricResult and analysis artifacts are append-only. Reanalysis does not overwrite v0.1 compatibility metrics or call DeepSeek by default.
- Input quality, lexical, connective and parser candidates remain automatic unverified signals requiring human review.
