# 智能英语写作反馈系统原型 v0.3

这是一个本地可运行、API-first、模块可替换的研究原型。v0.3 在 v0.2 本地 FastAPI/Repository 架构上增加可比较性、个人描述性基线、指标时间序列、问题轨迹和版本化 Learner Profile Snapshot。所有结果都是有限的原型证据，不是语言能力分数或经验证的成长判断。

本项目不是自动评分系统，不是完整 CALF 分析系统，也不能替代教师判断。所有规则均为 `prototype / heuristic / working assumption`，尚未经过教育实验验证。

## 1.1 安装（请按以下顺序执行）

新电脑推荐直接双击 `run.bat`，它会创建 Python 3.11 独立环境、安装依赖并启动。完整迁移说明见 [INSTALL.md](INSTALL.md)。

Step 1. 在运行安装命令之前，**先切换到项目所在目录（这里以你安装在C:\path\to\writing-feedback-mvp文件夹下为例，请按需调整路径）**：

```powershell
cd "C:\path\to\writing-feedback-mvp"
```

Step 2. 要求 Windows 11 和 CPython 3.11。所有命令均在项目根目录运行，无需激活环境;：

```powershell
py -V:Astral/CPython3.11.15 -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
```
若新电脑安装的是标准 Python 3.11，而非 Astral 发行版，将第一条命令替换为 `py -3.11 -m venv .venv`。
项目不会修改系统 Python 或系统环境变量。

## 1.2 启动

一键启动：双击 `run.bat`。

或分别启动后端和界面（两个终端）：

```powershell
& ".\.venv\Scripts\python.exe" -m scripts.migrate_database
& ".\.venv\Scripts\python.exe" -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000
& ".\.venv\Scripts\python.exe" -m streamlit run streamlit_app.py --server.port 8501
```

默认地址为：FastAPI `http://127.0.0.1:8000`、交互式 API 文档 `http://127.0.0.1:8000/docs`、Streamlit `http://127.0.0.1:8501`。在页面中填写匿名化 `student_id`、任务信息和作文后提交。数据库保存作文、指标、诊断、反馈、练习、历史、Provider/模型及版本元数据；API Key 需另行配置（见下）。

## 1.3 DeepSeek 配置
Step 1. 在[DSeek 开放平台](https://platform.deepseek.com/api_keys)创建账号后充值并创建一个专属API Key，获得API Key后页面保持不动，进行第二步；
Step 2. 在智能体安装文件夹下，复制 `.env.example` 为 `.env`，随后用记事本打开 `.env`。仅在本地填写 `DEEPSEEK_API_KEY` 对应的值，并按你的 DeepSeek 账户可用模型设置 `DEEPSEEK_MODEL`；其余配置可先沿用示例文件。不要在 README、聊天或提交记录中粘贴密钥。

`.env` 已被 Git 忽略。请勿把密钥写进代码、文档、数据库或提交记录。系统只在进程内检查密钥是否存在。缺少密钥、网络失败、API 错误或响应不符合 Pydantic Schema 时，会自动改用 `LocalDemoProvider`，同时保存实际 Provider、模型、`fallback_success` 状态和不含密钥的失败原因。

如需强制离线演示，可在 `.env` 设置 `LLM_PROVIDER=local`。当前 `LocalDemoProvider` 是无需另行部署模型的确定性演示实现。

## 1.4 测试与验证（使用人员不用看这一步，这一步仅作效果验证的说明）

```powershell
& ".\.venv\Scripts\python.exe" -m pytest tests -v
& ".\.venv\Scripts\python.exe" -m scripts.seed_demo_data
& ".\.venv\Scripts\python.exe" -m scripts.verify_closed_loop
& ".\.venv\Scripts\python.exe" -m scripts.smoke_stack
& ".\.venv\Scripts\python.exe" -m scripts.seed_longitudinal_data
```

`data/demo_students.json` 包含 3 个虚拟学生、每人 3 篇作文，覆盖持续性信号、描述性指标变化、历史不足和任务不可比较情形。`seed_demo_data` 生成 `data/demo_writing_feedback.db`；全部数据均为虚构。

实际验证结果见 [RUN_VERIFICATION.md](RUN_VERIFICATION.md)。

## 1.5 结构

- `app/analyzer`：可替换的 Analyzer 接口与基础分析器。
- `app/diagnosis`：可替换的 Diagnoser 接口与启发式规则。
- `app/llm`：Provider 接口、DeepSeek、LocalDemo 和自动回退路由。
- `app/services`：框架无关的提交应用服务。
- `app/repositories`：Student、Essay、Metric、Diagnosis、Feedback、Exercise、History、Profile、Configuration 和 SystemVersion 协议。
- `app/api`：FastAPI v1 路由和 API Schema。
- `app/feedback`：v0.1.1 兼容外壳、验证与诊断关联练习。
- `app/learner`：历史可比性判断和纵向摘要。
- `app/core`：v0.3 可比较性、基线、趋势、问题轨迹和 Snapshot 领域模型。
- `app/services/comparability.py`、`baseline.py`、`progress.py`、`learner_profile.py`：本地纵向引擎。
- `app/database`：SQLite Repository、事务与版本化迁移。
- `app/models`：Pydantic 输入、分析、诊断、反馈与结果模型。
- `app/ui`：Streamlit 页面和 HTTP API 客户端，不导入数据库、Analyzer、Diagnoser 或 Provider。

更多说明见 [架构](docs/ARCHITECTURE.md)、[数据模型](docs/DATA_MODEL.md)、[升级路径](docs/UPGRADE_PATH.md)和[已知限制](docs/KNOWN_LIMITATIONS.md)。

## 1.6 当前限制

v0.3 的所有阈值仍是工作假设，尚未完成文献校准、教学效度、测量效度、公平性或跨任务稳定性研究。SQLite 适合本地研究原型；PostgreSQL、微信小程序和云部署均未实现。任何方向都只能称为“观察到的指标趋势”，不能被解释为真实能力变化。
