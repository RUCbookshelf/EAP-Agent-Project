# English Writing Feedback Prototype v0.9.2.1

v0.9.3-C 完成产品旅程加固：Learning Journey 不再永久为空。旅程事件由权威
来源记录（作文、分析、反馈、练习、作答、评价、修订、任务内响应）在读取时
推导，每个事件都可追溯至真实记录；空状态按缺失阶段准确分类；提供确定性
合成演示学习者 `DEMO-001` 的可重复/幂等/可清理设置；Student ID 归一化与
跨页学习者一致性；练习与修订幂等。任何旅程输出均不构成掌握、习得、学习
增益、因果、迁移、熟练度或 CEFR 声明。详见 [v0.9.3-C 规格](docs/development/V0.9.3_C_SPEC.md)
与 [v0.9.3-C 验收](RUN_VERIFICATION_V0.9.3_C.md)、
[v0.9.3 集成验收](RUN_VERIFICATION_V0.9.3.md)。

v0.9.1 新增基于角色的双视图界面（学生视图/研究视图）、渐进式信息披露和响应式布局。（英文/简体中文）、CALF 指标分类展示与统一卡片布局、以及角色分离视图。所有用户可见文本已迁移至 `locales/` 下的语言文件。详见 [v0.8.1 规格](docs/development/V0.8.1_SPEC.md)。

v0.8 新增 CALF Measurement Foundation：4 个构念、22 个测量规范、14 个分析单位，以及 MTLD、HD-D、句法候选单位、错误标注基础和基于真实时长的写作输出率。它们是可审计的研究测量/候选基础，不是 CALF 总分、作文评分、能力/熟练度/CEFR 判断。Accuracy 与词汇复杂度中的 sophistication 保持不可用；句法候选不进入诊断、优先级或纵向比较。详见 [CALF Measurement](docs/CALF_MEASUREMENT.md) 与 [v0.8 verification](RUN_VERIFICATION_V0.8.md)。

v0.7.1 是 v0.7 的可靠性与界面修复版。后端现在确定性生成结构化纵向状态，区分跨任务历史与同一任务多稿；Provider 状态明确区分外部成功、服务端局部修复、请求/解析/验证/纠错失败及 LocalDemo 回退。Streamlit 提供 Feedback、Revision、Progress、Evidence、Research Audit 五个 Tab，以及学生/研究者视图切换和有解释的空状态。详见 [UI design](docs/UI_DESIGN.md)、[Provider status](docs/PROVIDER_STATUS.md) 与 [Within-task trajectory](docs/WITHIN_TASK_REVISION_TRAJECTORY.md)。

仍不得把任何状态、轨迹或 Positive Finding 解释为能力、熟练度、学习增长、CEFR 或整体评分。运行与验收记录见 [RUN_VERIFICATION_V0.7.1.md](RUN_VERIFICATION_V0.7.1.md)。

v0.7 将原有纵向模块升级为任务感知、版本隔离、证据可追溯的 Learner Model 2.0。系统先选择每个修订任务的代表稿，再按写作条件建立 Task Cluster；Metric 与 Diagnostic Trajectory 只在兼容集内计算。当前学习目标只能来自当前作文已通过 Diagnostic Gate 且证据相关性已验证的诊断，允许零目标。

研究者可在 Streamlit 的 **Learner Model audit** 查看代表稿、排除原因、数据充分性、轨迹、学习目标和 History Evidence；学生视图只显示简化后的当前关注点。所有输出仍是形成性研究原型，不是能力、进步、CEFR、CALF 或作文总分。详见 [Learner Model](docs/LEARNER_MODEL.md) 与 [API](docs/API.md)。

## v0.6.1 retained baseline

v0.6.1 新增独立诊断校准层：指标可信度、诊断准入、透明优先级、证据相关性验证，以及受准入结果约束的 DeepSeek/LocalDemo 反馈和练习。自动指标仍只是研究原型信号，不是能力、CEFR、CALF 或作文总分。

v0.6 在修订分析基础上新增 API 驱动的学习者时间线、版本分段指标图、问题轨迹、修订比较、本地研究者管理界面、非敏感配置版本/验证/激活/回滚、注册表和追加式重分析。它仍是本地研究原型，不是能力评分、CALF 总分、CEFR、班级排名或可公开部署的管理系统。

这是一个本地可运行、API-first、模块可替换的研究原型。v0.4 在既有纵向引擎上增加可插拔 spaCy 英语分析、输入质量提醒、版本化 Metric Registry 和追加式 AnalysisRun。所有结果都是有限的自动分析信号，不是语言能力分数或经验证的成长判断。

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
- `app/analysis`：spaCy Analyzer、资源检查、输入质量、词汇/衔接/句法特征与版本化注册表。
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

## 1.6 v0.6.1 诊断校准

研究者可在 Streamlit 侧栏进入 **Diagnostic audit**，查看 raw、monitored、eligible、selected、suppressed 信号及原因；学生页面只显示经筛选的反馈。词汇指标保存可复算 token 口径，句法输出保持 candidate 命名。详见 [Diagnostic Calibration](docs/DIAGNOSTIC_CALIBRATION.md)、[Evidence Validation](docs/EVIDENCE_VALIDATION.md) 和 [人工评审指南](docs/development/V0.6.1_HUMAN_REVIEW_GUIDE.md)。

普通测试不调用付费 API。显式真实验证命令：

```powershell
$env:RUN_LIVE_LLM_TESTS='1'
& ".\.venv\Scripts\python.exe" -m scripts.verify_live_deepseek_v061
```

## 1.7 当前限制

v0.3 的所有阈值仍是工作假设，尚未完成文献校准、教学效度、测量效度、公平性或跨任务稳定性研究。SQLite 适合本地研究原型；PostgreSQL、微信小程序和云部署均未实现。任何方向都只能称为“观察到的指标趋势”，不能被解释为真实能力变化。

v0.4 使用固定的 `spaCy 3.8.7` 与 `en_core_web_sm 3.8.0`。解析、词性、词元、名词短语、句法和连接表达仍可能误判学习者文本；MATTR、lexical density 和所有阈值都是可替换的原型参数，不是 CALF 总分或能力测量。模型缺失时会显式记录并回退 BasicAnalyzer。
