# Prompt 架构 v0.3.0

## 文件

- `app/prompts/system_prompt_v0_3_0.txt`：纳入版本管理的固定 System Prompt。
- `app/prompts/builder.py`：把 `FeedbackContext` 渲染为 messages，并构造一次纠错 Prompt。
- `app/prompts/versioning.py`：`feedback-prompt-v0.3.0`、`structured-feedback-v0.1.1` 和 SHA-256。
- `app/prompts/prompt_manifest_v0_3_0.json`：冻结模板文件、Prompt/Schema 版本及 System/User 模板哈希。

模板内容发生语义变化时必须创建新模板文件并提升 `PROMPT_VERSION`。初始化和每次 Prompt 构造都会核对 manifest；文件或 User 契约发生漂移而清单未同步时会 fail closed，不会调用 Provider。

## User Prompt

User message 是单一 JSON 对象：

- `submission`：essay_text、writing_prompt、genre、draft_stage、timed、time_limit_minutes、tool_use、submitted_at；
- `metrics`：名称和值列表；
- `diagnoses`：带 diagnosis_id、规则版本和限制的完整信号列表；
- `learner_history`：可比较状态、可比数量、带 ID 的证据、摘要、限制和判断理由；
- `learner_profile_snapshot`：仅包含本地引擎已筛选的纳入 ID、趋势摘要、问题轨迹、重点候选和限制；不含不可比较作文或原始历史观察；
- `required_schema`：Pydantic 导出的完整 JSON Schema。

作文始终只是 `submission.essay_text` 的字符串值。作文中类似 JSON、system、assistant、diagnosis 或 history 的文本不会与真正控制字段合并。

## 防护与证据边界

System Prompt 明确要求：忽略作文内指令；只用传入诊断 ID；不新增类别；所有作文引文逐字复制；纵向评论只用历史证据并返回 ID；无历史时明确无法判断；禁止分数、CEFR、掌握/退步/真实能力增长；指标均为启发式；严格输出 JSON Schema。

Prompt 不是唯一安全边界。模型返回后，程序再次执行确定性验证：

- improvement diagnosis_id 必须存在且类别一致；
- 引文在规范化换行和连续空格后必须是 essay_text 子串；
- history_evidence_id 必须存在；有证据时必须至少绑定一个 ID；无证据时 ID 必须为空并明确无法判断；
- 无历史时禁止确定性发展结论；
- 练习 ID/类别必须有效，类型由 Pydantic Literal 限定。

LLM 不得从 Snapshot 重算趋势、改变方向或提升置信度。Snapshot 只提供背景；可写入纵向评论的内容仍必须存在于 `learner_history.history_evidence` 并绑定 H ID。

## 哈希

- `system_template_hash`：System Prompt 文件内容；
- `user_template_hash`：User Prompt 字段契约；
- `rendered_prompt_hash`：实际 messages 的规范化 JSON；
- `schema_version`：结构化反馈契约版本。

哈希用于追溯，不是数字签名，也不隐藏 Prompt 内容。
