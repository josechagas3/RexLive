@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" app.py
  goto fim
)
where python >nul 2>nul
if not errorlevel 1 (
  python app.py
  goto fim
)
where py >nul 2>nul
if not errorlevel 1 (
  py -3 app.py
  goto fim
)
if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" (
  "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" app.py
  goto fim
)
echo Python 3.10 ou superior nao encontrado. Instale Python e tente novamente.
:fim
pause
