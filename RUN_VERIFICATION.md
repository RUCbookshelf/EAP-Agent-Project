# v0.1 / v0.1.1 运行验证记录

> 下方前半部分保留 v0.1 基线与可移植性记录；文末“v0.1.1 最终复核”是当前有效状态。

验证日期：2026-07-29（Asia/Shanghai）  
项目路径：`A:\坚果云同步\TheBookshelf's Academia\F-Project\03-学术论文写作智能体\writing-feedback-mvp`

## 实际执行命令

```powershell
py -V:Astral/CPython3.11.15 -m venv "...\writing-feedback-mvp\.venv"
& ".\.venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements.txt
& ".\.venv\Scripts\python.exe" -m pip check
& ".\.venv\Scripts\python.exe" -m compileall -q app scripts tests
& ".\.venv\Scripts\python.exe" -m pytest tests -v
& ".\.venv\Scripts\python.exe" -m scripts.seed_demo_data
& ".\.venv\Scripts\python.exe" -m scripts.verify_closed_loop
& ".\.venv\Scripts\python.exe" -m scripts.smoke_streamlit
```

所有项目 Python 命令均使用 `.venv\Scripts\python.exe`；未激活 PowerShell 脚本，未安装到 Agent 环境，未修改系统 Python 或系统环境变量。

## 实际结果

| 验证项 | 结果 | 证据摘要 |
|---|---|---|
| Python 环境 | PASS | CPython 3.11.15；pip 位于项目 `.venv` |
| 依赖 | PASS | 安装完成；`pip check` 报告 `No broken requirements found` |
| 静态导入/编译 | PASS | `compileall` 成功 |
| pytest | PASS | 12 collected，12 passed；最终复核 1.11 秒 |
| Streamlit 测试 | PASS | pytest `AppTest` 无异常 |
| Streamlit 实际启动 | PASS | 端口 8523，HTTP 200；验证后正常终止进程 |
| 模拟数据 | PASS | 3 个虚拟学生、9 篇作文、9 组指标/诊断/反馈/历史、31 项练习 |
| 第一次真实闭环提交 | PASS | `VERIFY001` essay_id=1；保存、分析、诊断、回退反馈和练习均完成 |
| 第二次同生提交 | PASS | essay_id=2；读取 1 条可比历史并生成纵向描述 |
| 验证数据库 | PASS | 1 student、2 essays、2 metrics、2 diagnoses、2 feedback、7 exercises、2 history、4 system versions |
| DeepSeek（v0.1 基线） | FALLBACK_PASS | 当时 Key 尚未配置；LocalDemo 自动接管，状态为 `fallback_success`。该状态已被文末 v0.1.1 真实验证取代 |
| 敏感信息扫描 | PASS | 排除虚拟环境、数据库和本地 `.env` 后，未发现嵌入式 Key 样式值 |

本段记录的是 v0.1 基线：当时只完成模拟 API 与回退验证。当前真实 DeepSeek 结果见文末 v0.1.1 最终复核。

## 已完成功能

- [x] Streamlit 网页可启动
- [x] 用户可提交作文和任务信息
- [x] SQLite 保存全部规定实体，且不保存 API Key
- [x] 独立 Analyzer 返回 8 个基础指标、版本和限制
- [x] 独立 Diagnosis 最多返回 1 个优点、2 个改进重点，并带证据、来源指标、置信度和限制
- [x] DeepSeekProvider 与 LocalDemoProvider 可替换
- [x] API 缺 Key/失败/格式错误自动回退并记录实际 Provider、模型和状态
- [x] StructuredFeedback 由 Pydantic 验证
- [x] 生成错误识别、句子改写、短写作迁移三类诊断关联练习
- [x] 再次提交时读取历史；不可比或无历史时明确报告数据不足
- [x] 生成不声称能力提升的纵向描述
- [x] 3 名虚拟学生、每人 3 篇作文
- [x] 12 项 pytest 测试通过
- [x] 架构、数据模型、升级路径和限制文档完成

## 修复记录

首次按文件路径运行 `scripts\seed_demo_data.py` 时，Python 的模块路径只包含 `scripts`，出现 `ModuleNotFoundError: app`。已将 `scripts` 设为包，并统一使用 `python -m scripts.<name>`；随后种子与闭环验证通过。第一次后台启动方式受本机命令执行策略拦截，改用可复现的 `scripts.smoke_streamlit` 子进程 + HTTP 检查，不修改系统策略，验证通过。

## 当前限制

所有分析与诊断仍是未经教育实验验证的工作假设，不是完整 CALF 或能力评价。历史比较控制变量有限。LocalDemo 仅生成模板化反馈；Pydantic 只能验证结构。SQLite 和 Streamlit 适合研究原型，不具备生产环境的身份认证、加密、多租户、迁移和隐私治理能力。详细内容见 `docs/KNOWN_LIMITATIONS.md`。

## 可移植性追加验证

验证日期：2026-07-29（Asia/Shanghai）

本轮没有复用项目 `.venv`。验证程序首先确认以下临时路径不存在，然后由 `run.bat --install-only` 从零创建：

`C:\Users\16073\AppData\Local\Temp\writing-feedback-mvp-portability-20260729085718`

实际流程：

```powershell
$env:WRITING_FEEDBACK_VENV="C:\Users\16073\AppData\Local\Temp\writing-feedback-mvp-portability-20260729085718"
cmd.exe /d /c "call run.bat --install-only"
& "$env:WRITING_FEEDBACK_VENV\Scripts\python.exe" --version
& "$env:WRITING_FEEDBACK_VENV\Scripts\python.exe" -m pip check
& "$env:WRITING_FEEDBACK_VENV\Scripts\python.exe" -m pytest tests -q
& "$env:WRITING_FEEDBACK_VENV\Scripts\python.exe" -m scripts.smoke_streamlit --python "$env:WRITING_FEEDBACK_VENV\Scripts\python.exe"
```

结果：

- `run.bat` 成功发现 CPython 3.11.15、创建全新环境并从 `requirements.txt` 安装全部依赖；
- 新环境报告 `Python 3.11.15`；
- `pip check`：`No broken requirements found`；
- 新环境 pytest：`12 passed in 1.76s`；
- Streamlit 使用该临时环境的 Python 启动，端口 8523 返回 HTTP 200；
- 启动冒烟测试完成后服务进程正常终止；
- `.gitignore` 已明确包含 `.venv/`、`.env`、`__pycache__/`、`**/__pycache__/`、`*.pyc` 和 `*.db`。

结论：新电脑在已安装 Python 3.11 且首次安装时可联网的前提下，可通过 `run.bat` 从零建立隔离环境并启动 v0.1。

## v0.1.1 最终复核

复核日期：2026-07-29（Asia/Shanghai）。

实际执行：

```powershell
& ".\.venv\Scripts\python.exe" -m pytest tests -q
cmd.exe /d /c "call run.bat --verify"
& ".\.venv\Scripts\python.exe" -m scripts.audit_live_verification
& ".\.venv\Scripts\python.exe" -m pip check
& ".\.venv\Scripts\python.exe" -m compileall -q app scripts tests
```

真实 DeepSeek 验证此前使用进程级 `RUN_LIVE_LLM_TESTS=1` 执行：

```powershell
& ".\.venv\Scripts\python.exe" -m scripts.verify_live_deepseek
```

最终结果：

| 验证项 | 结果 | 直接证据 |
|---|---|---|
| pytest | PASS | `42 passed, 1 skipped in 2.26s`；唯一 skip 是默认关闭的外部 live test |
| 依赖与编译 | PASS | `pip check` 无损坏依赖；`compileall` 成功 |
| `run.bat --verify` | PASS | 识别 Python 3.11、现有隔离环境、`.env`、数据库和 Prompt manifest；Streamlit 返回 HTTP 200 |
| 两次真实 DeepSeek 提交 | PASS | submission `E000001`、`E000002` 均由 `deepseek` / `deepseek-v4-flash` 返回 |
| 第二次历史输入 | PASS | 第二次请求包含 2 条结构化历史证据 |
| 历史引用验证 | PASS | 返回 `H001`、`H002`；均在 allowlist 内，`validation_status=passed` |
| 重试与回退 | PASS | `retry_count=0`，`fallback=false` |
| 持久化 | PASS | 两次作文、分析、诊断、反馈、练习、历史与调用审计写入 `data/live_deepseek_verification.db` |
| 密钥保护 | PASS | 初始化器与审计仅报告“已配置”布尔值；数据库没有 API Key 列，验证报告不保存 Key |

真实验证报告位于 `data/live_deepseek_verification.json`；`scripts.audit_live_verification` 对报告和 SQLite 的独立复核结果为 `PASS`。较早的 `data/live_deepseek_verification_blocker.json` 是配置完成前的历史证据，已被本次成功结果取代。

结论：v0.1.1 的真实双提交纵向反馈闭环、自动验证、数据库保存、Windows 启动和普通测试均已通过。此结论只证明原型链路可运行，不代表教学效度或学生能力测量有效。
