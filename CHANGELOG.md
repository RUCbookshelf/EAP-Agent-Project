# Changelog

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
