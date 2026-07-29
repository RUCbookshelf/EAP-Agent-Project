# Local development

Requirements: Windows, Python 3.11, and network access for first dependency installation. No activation script is required.

`run.bat` creates/reuses `.venv`, installs `requirements.txt`, allows LocalDemo when no environment file exists, runs migrations, checks Prompt assets, starts FastAPI, polls health, then starts Streamlit.

Default local URLs:

- FastAPI: `http://127.0.0.1:8000`
- API docs: `http://127.0.0.1:8000/docs`
- Streamlit: `http://127.0.0.1:8501`

Configuration names are documented in `.env.example`. Override ports consistently; `API_BASE_URL` must address the configured FastAPI host/port. Occupied ports cause a clear failure and are never silently changed.

Useful commands:

```powershell
& ".\.venv\Scripts\python.exe" -m scripts.migrate_database
& ".\.venv\Scripts\python.exe" -m pytest tests -q
cmd.exe /d /c "call run.bat --verify"
```

All services remain local. No cloud account, domain, PostgreSQL, Redis, Kubernetes or WeChat AppID is required.
