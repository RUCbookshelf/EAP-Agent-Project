# v0.1.1 完成标准审计

审计原则：只有直接代码、自动测试、数据库、运行输出或真实外部调用才能作为证据。“代码看起来支持”不等于真实 API 已验证。

| # | 完成标准 | 状态 | 当前直接证据 |
|---|---|---|---|
| 1 | 写作任务元数据真实进入 DeepSeek 请求 | PASS_LIVE | 本地 transport 测试核对实际 request body；真实两次提交均由 DeepSeek 返回，审计记录对应 Prompt 版本与哈希 |
| 2 | Prompt 模板模块化 | PASS | `system_prompt_v0_1_1.txt`、`builder.py`、`versioning.py` 和受检 `prompt_manifest_v0_1_1.json` |
| 3 | diagnosis_id 和 history_evidence_id | PASS | Pydantic 格式约束、Diagnoser/HistoryService、ID 连续性测试 |
| 4 | 模型只能围绕有效诊断反馈 | PASS | improvement ID allowlist、类别一致性、未知 ID 失败测试 |
| 5 | 所有作文引文可验证 | PASS | 空白规范化后的严格子串验证；虚构/合法引文测试 |
| 6 | 纵向评论绑定有效历史证据 | PASS | 有历史时至少一个有效 ID；未知/空绑定失败测试 |
| 7 | 无历史时无确定性发展判断 | PASS | ID 必须为空、必须明确无法判断、英中多类确定性措辞测试 |
| 8 | Prompt 和 Schema 可追溯 | PASS | 版本、三类 SHA-256、Schema version、参数和时间入库测试；manifest 漂移检查 fail closed |
| 9 | 普通测试全部通过 | PASS | 当前最终测试输出；live 测试默认唯一 skip |
| 10 | 真实 DeepSeek 两次提交成功或真实外部阻塞证据 | PASS_LIVE | `verify_live_deepseek` 完成同一虚拟学生两次真实提交；两次 Provider 均为 `deepseek`，无回退 |
| 11 | 第二次真实请求含非空结构化历史证据 | PASS_LIVE | 独立审计确认第二次请求含 2 条历史证据 |
| 12 | 第二次真实反馈引用有效 history_evidence_id | PASS_LIVE | 返回 `H001`、`H002`，通过 allowlist 和完整后置验证；`validation_status=passed` |
| 13 | 不合格 DeepSeek 结果不保存为正式反馈 | PASS | 两次失败后数据库正式记录为 LocalDemo；失败主响应文本不存在于 feedback JSON |
| 14 | run.bat 与当前项目同步 | PASS | Python、pip、依赖、`.env`、数据库、Prompt 和入口均已更新 |
| 15 | run.bat 实际启动验证 | PASS | 现有环境和全新环境均由 `cmd.exe` 调用，Streamlit HTTP 200 |
| 16 | 文档与代码一致 | PASS | 状态、运行记录、限制和审计均已更新为本次真实 API 实测结果 |
| 17 | v0.1 有效功能未破坏 | PASS | 原 Analyzer/Diagnosis/历史/Provider/UI/SQLite 闭环测试继续通过；v0.1 Schema 迁移测试通过 |

## 当前结论

17 项完成标准均已有直接证据。`data/live_deepseek_verification.json` 报告 `status=PASS`；独立数据库审计确认第二次请求包含 2 条结构化历史证据，反馈引用有效 `H001`、`H002`，后置验证通过且未发生重试或回退。v0.1.1 完成门已通过。
