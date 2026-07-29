# 项目状态

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
