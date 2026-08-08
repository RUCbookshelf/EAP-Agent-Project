@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

set "PYTHONUTF8=1"
if not defined WRITING_FEEDBACK_VENV set "WRITING_FEEDBACK_VENV=.venv"
set "WF_VENV_PATH=%WRITING_FEEDBACK_VENV%"

echo [1/7] Bootstrapping environment...
powershell -NoProfile -ExecutionPolicy Bypass -File "scripts\dev\bootstrap_environment.ps1"
if errorlevel 1 goto :bootstrap_failed

if defined WRITING_FEEDBACK_VENV (
    set "VENV_PYTHON=%WRITING_FEEDBACK_VENV%\Scripts\python.exe"
) else (
    set "VENV_PYTHON=%~dp0.venv\Scripts\python.exe"
)
if not exist "%VENV_PYTHON%" (
    echo ERROR: Environment was bootstrapped but "%VENV_PYTHON%" was not found.
    goto :failed
)

echo [2/7] Verifying NLP resources...
"%VENV_PYTHON%" -m scripts.verify_nlp_resources
if errorlevel 1 (
    echo WARNING: NLP resource check reported issues. BasicAnalyzer fallback may be active.
)

echo [3/7] Checking optional local configuration...
set "ENV_CHECK_FILE=.env"
if defined WRITING_FEEDBACK_ENV_FILE set "ENV_CHECK_FILE=%WRITING_FEEDBACK_ENV_FILE%"
if not exist "%ENV_CHECK_FILE%" (
    echo INFO: No environment file was found. Copy .env.example to .env to configure DeepSeek.
    echo INFO: Continuing safely in LocalDemo mode.
    if not defined LLM_PROVIDER set "LLM_PROVIDER=local"
) else (
    echo INFO: Environment file found. Configuration values will be loaded by the application.
)

if /I "%~1"=="--verify" (
    echo [5/5] Running isolated FastAPI, docs, and Streamlit startup verification...
    "%VENV_PYTHON%" -m scripts.verify_launcher
    if errorlevel 1 goto :start_failed
    echo run.bat verification completed successfully.
    exit /b 0
)

echo [4/7] Applying versioned database migrations...
"%VENV_PYTHON%" -m scripts.migrate_database
if errorlevel 1 goto :migration_failed

echo [5/7] Checking data directories, database, and prompt templates...
"%VENV_PYTHON%" -m scripts.initialize_project
if errorlevel 1 goto :initialize_failed

if /I "%~1"=="--install-only" (
    echo Installation and initialization verification completed successfully.
    exit /b 0
)

echo [6/7] Starting FastAPI and the Streamlit API client for v0.8...
echo Keep this window open while using the application. Press Ctrl+C to stop.
"%VENV_PYTHON%" -m scripts.run_local
if errorlevel 1 goto :start_failed
exit /b 0

:bootstrap_failed
echo ERROR: Environment bootstrap failed. See messages above for details.
echo Common fixes:
echo   - Install uv: powershell -ExecutionPolicy Bypass -c "iwr https://astral.sh/uv/install.ps1 -UseBasicParsing | iex"
echo   - Or: python -m pip install uv
echo Then re-run this file.
goto :failed

:initialize_failed
echo ERROR: Data directories, database schema, or prompt templates could not be initialized.
goto :failed

:migration_failed
echo ERROR: The versioned database migration did not complete. Existing data was not deleted.
goto :failed

:start_failed
echo ERROR: FastAPI or Streamlit stopped with an error. Check whether ports 8000 or 8501 are occupied.
goto :failed

:failed
if "%~1"=="" pause
exit /b 1
