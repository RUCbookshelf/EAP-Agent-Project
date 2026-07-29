# Changelog

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
