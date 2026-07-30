@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

set "PYTHONUTF8=1"
if not defined WRITING_FEEDBACK_VENV set "WRITING_FEEDBACK_VENV=.venv"
set "VENV_PYTHON=%WRITING_FEEDBACK_VENV%\Scripts\python.exe"

echo [1/7] Checking for Python 3.11 and the isolated project environment...
if not exist "%VENV_PYTHON%" (
    py -V:Astral/CPython3.11.15 --version >nul 2>&1
    if not errorlevel 1 (
        py -V:Astral/CPython3.11.15 -m venv "%WRITING_FEEDBACK_VENV%"
    ) else (
        py -3.11 --version >nul 2>&1
        if errorlevel 1 goto :python_missing
        py -3.11 -m venv "%WRITING_FEEDBACK_VENV%"
    )
    if errorlevel 1 goto :venv_failed
)

"%VENV_PYTHON%" -c "import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 11) else 1)"
if errorlevel 1 goto :wrong_python

echo [2/7] Ensuring pip is available and installing project dependencies...
"%VENV_PYTHON%" -m ensurepip --upgrade >nul
if errorlevel 1 goto :pip_failed
"%VENV_PYTHON%" -m pip install --disable-pip-version-check -r requirements.txt
if errorlevel 1 goto :install_failed

echo [3/7] Installing and checking the pinned English NLP resource...
"%VENV_PYTHON%" -m scripts.verify_nlp_resources --require-model >nul 2>&1
if errorlevel 1 (
    "%VENV_PYTHON%" -m pip install --disable-pip-version-check -r requirements-nlp.txt
    if errorlevel 1 (
        echo WARNING: The English spaCy model could not be installed. BasicAnalyzer fallback will remain available and visible in health status.
    )
)
"%VENV_PYTHON%" -m scripts.verify_nlp_resources

echo [4/7] Checking optional local configuration...
set "ENV_CHECK_FILE=.env"
if defined WRITING_FEEDBACK_ENV_FILE set "ENV_CHECK_FILE=%WRITING_FEEDBACK_ENV_FILE%"
if not exist "%ENV_CHECK_FILE%" (
    echo INFO: No environment file was found. Copy .env.example to .env to configure DeepSeek.
    echo INFO: Continuing safely in LocalDemo mode.
    if not defined LLM_PROVIDER set "LLM_PROVIDER=local"
) else (
    echo INFO: Environment file found. Configuration values will be loaded by the application.
)

echo [5/7] Applying versioned database migrations...
"%VENV_PYTHON%" -m scripts.migrate_database
if errorlevel 1 goto :migration_failed

echo [6/7] Checking data directories, database, and prompt templates...
"%VENV_PYTHON%" -m scripts.initialize_project
if errorlevel 1 goto :initialize_failed

if /I "%~1"=="--install-only" (
    echo Installation and initialization verification completed successfully.
    exit /b 0
)

if /I "%~1"=="--verify" (
    echo [7/7] Running bounded FastAPI, docs, and Streamlit startup verification...
    "%VENV_PYTHON%" -m scripts.smoke_stack --python "%VENV_PYTHON%"
    if errorlevel 1 goto :start_failed
    echo run.bat verification completed successfully.
    exit /b 0
)

echo [7/7] Starting FastAPI and the Streamlit API client for v0.8...
echo Keep this window open while using the application. Press Ctrl+C to stop.
"%VENV_PYTHON%" -m scripts.run_local
if errorlevel 1 goto :start_failed
exit /b 0

:python_missing
echo ERROR: Python 3.11 was not found. Python 3.14 will not be used.
echo Install 64-bit Python 3.11 with the Windows py launcher, then run this file again.
goto :failed

:venv_failed
echo ERROR: The project virtual environment could not be created.
goto :failed

:wrong_python
echo ERROR: The selected virtual environment is not running Python 3.11.
goto :failed

:pip_failed
echo ERROR: pip could not be initialized inside the project virtual environment.
goto :failed

:install_failed
echo ERROR: Project dependencies could not be installed. Check the internet connection and retry.
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
