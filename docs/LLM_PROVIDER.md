# LLM Provider through v0.3

## 职责边界

`DeepSeekProvider` 只负责接收已经构造好的 messages、发送 OpenAI-compatible 请求、解析响应并执行 Pydantic Schema 验证。教学规则、证据约束和 Prompt 拼接不在 Provider 内。

`LocalDemoProvider` 使用同一个结构化 User Prompt 生成确定性、可验证的离线反馈。它不是语言模型，也不代表真实教学判断。

`ProviderRouter` 负责 Prompt 构建、后置证据验证、一次纠错重试、回退和调用审计。

v0.3 的 FeedbackContext 可携带筛选后的 Learner Profile Snapshot。不可比较作文和原始历史观察不会发送；本地引擎先把可用趋势/问题轨迹转换为 H 证据 ID，Provider 的纵向评论仍由现有 ID 后置验证约束。

## 调用顺序

1. `PromptBuilder` 构造版本化 System/User messages。
2. 主 Provider 返回通过 Pydantic 的 `StructuredFeedback`。
3. `FeedbackValidator` 验证 ID、类别、逐字引文、历史绑定和练习。
4. Schema 或证据验证失败时，追加明确纠错消息并重试一次。
5. 第二次失败时，LocalDemo 生成并通过同一后置验证。
6. 只有最终合格反馈写入 `feedback_records`；每次尝试写入 `llm_call_records`。

缺 Key 属于配置失败，不进行无意义重试，直接回退且 `retry_count=0`。网络/API 失败保留失败类型，但不保存 Key。

## 审计字段

每次调用记录 Prompt 版本、System/User 模板哈希、rendered Prompt 哈希、Schema 版本、Provider、模型、temperature、请求/响应时间、成功状态、验证状态、retry_count 和 fallback_reason。

数据库不保存 Authorization Header、API Key、完整请求消息或未验证的模型响应。

## 模式切换

- `LLM_PROVIDER=local`：LocalDemo。
- `LLM_PROVIDER=deepseek`：DeepSeek 主 Provider，失败时安全回退。
- 缺 `.env` 时 `run.bat` 在本次进程设置 LocalDemo；不修改系统环境变量。

真实集成测试只在 `RUN_LIVE_LLM_TESTS=1` 时运行。
