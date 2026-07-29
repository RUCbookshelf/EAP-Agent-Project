# 新电脑安装指南

本指南适用于 Windows 11。项目只使用 Python 3.11，不需要 PowerShell 激活脚本，也不会修改系统级环境变量或已有 Python 安装。

## 1. 新电脑准备

1. 安装 64 位 CPython 3.11，并确保同时安装 Windows `py` launcher。
2. 打开“命令提示符”或 PowerShell，运行：

   ```powershell
   py -3.11 --version
   ```

   输出必须以 `Python 3.11` 开头。如果系统注册了 Astral 发行版，也可使用 `py -V:Astral/CPython3.11.15 --version`。
3. 首次安装依赖需要互联网连接。运行应用本身可使用 LocalDemo 离线反馈；调用 DeepSeek 需要网络。

## 2. 复制项目

将整个 `writing-feedback-mvp` 文件夹复制或解压到新电脑。路径可以包含中文、空格和单引号。

迁移时不要复制以下机器相关或敏感内容：

- `.venv`：必须在新电脑重新创建；
- `.env`：可能包含本机 API Key，应在新电脑单独、安全地配置；
- `*.db`：包含本地作文与反馈数据，除非经过授权并确实需要迁移；
- `__pycache__` 和 `*.pyc`：Python 临时文件。

项目至少应包含 `run.bat`、`requirements.txt`、`streamlit_app.py`、`app`、`data`、`docs` 和 `tests`。

## 3. 一键安装并启动

双击项目根目录中的 `run.bat`。

它会依次：

1. 切换到 `run.bat` 所在目录，因此不依赖用户当前路径；
2. 优先查找指定的 Astral CPython 3.11.15，否则查找标准 `py -3.11`；
3. 在项目内创建 `.venv`；
4. 使用 `.venv\Scripts\python.exe` 安装或核对 `requirements.txt`；
5. 安装并检查 `requirements-nlp.txt` 中固定的 spaCy 英语模型；模型失败时明确保留 BasicAnalyzer 回退；
6. 检查环境确实是 Python 3.11；
7. 执行版本化数据库迁移；
8. 启动 FastAPI，等待 health endpoint 正常；
9. 启动 Streamlit API 客户端。

默认 FastAPI 为 `http://127.0.0.1:8000`，API 文档为 `http://127.0.0.1:8000/docs`，Streamlit 为 `http://127.0.0.1:8501`。使用期间不要关闭启动窗口；按 `Ctrl+C` 可停止两项服务。

后续再次双击时会复用 `.venv`，并再次核对依赖，不会向系统 Python 安装项目包。

## 4. 可选的 DeepSeek 配置

不配置 API Key 也能运行，系统会使用 LocalDemoProvider。

如需 DeepSeek：

1. 将 `.env.example` 复制为 `.env`；
2. 只在新电脑本地填写 `DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL` 和 `DEEPSEEK_MODEL`；
3. 保持 `LLM_PROVIDER=deepseek`；
4. 重新启动 `run.bat`。

不要通过聊天、邮件或版本控制传递 `.env`。程序不会把 API Key 写进数据库。

## 5. 命令行安装方式

如果不使用批处理，可在项目根目录运行：

```powershell
py -V:Astral/CPython3.11.15 -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt
& ".\.venv\Scripts\python.exe" -m pip install -r requirements-nlp.txt
& ".\.venv\Scripts\python.exe" -m scripts.verify_nlp_resources
& ".\.venv\Scripts\python.exe" -m scripts.migrate_database
& ".\.venv\Scripts\python.exe" -m scripts.run_local
```

标准 Python 3.11 安装没有 Astral 标识时，将第一行替换为：

```powershell
py -3.11 -m venv .venv
```

## 6. 安装后检查

```powershell
& ".\.venv\Scripts\python.exe" --version
& ".\.venv\Scripts\python.exe" -m pip check
& ".\.venv\Scripts\python.exe" -m pytest tests -q
```

预期 Python 为 3.11，`pip check` 显示无依赖冲突，测试全部通过。

## 7. 常见问题

- 提示找不到 Python：重新安装 Python 3.11 并勾选/安装 `py launcher`，然后确认 `py -3.11 --version` 可用。
- 依赖下载失败：检查网络、代理和防火墙后再次运行 `run.bat`。已成功安装的包会被复用。
- 端口 8000 或 8501 被占用：先关闭占用程序，或在 `.env` 中一致设置 `API_PORT`、`STREAMLIT_PORT` 和 `API_BASE_URL`；系统不会静默改用其他端口。
- DeepSeek 不可用：系统应自动回退到 LocalDemo，并显示 `fallback_success`；不要把 API Key 发给维护人员排查。
- 数据库需要重新开始：先自行备份 `data` 中需要保留的数据库，再由项目负责人决定数据清理方式。
