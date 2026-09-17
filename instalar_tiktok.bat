@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto instalar
where python >nul 2>nul
if not errorlevel 1 (
  python -m venv .venv
  goto verificar
)
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -m venv .venv
  goto verificar
)
if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" (
  "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -m venv .venv
  goto verificar
)
echo Instale Python 3.10 ou superior antes de continuar.
goto fim
:verificar
if not exist ".venv\Scripts\python.exe" (
  echo Nao foi possivel criar o ambiente Python.
  goto fim
)
:instalar
".venv\Scripts\python.exe" -m pip install -r requirements-tiktok.txt
if errorlevel 1 (
  echo A instalacao falhou. Confira a conexao com a internet e tente novamente.
  goto fim
)
echo Instalacao concluida. Encerre o servidor anterior e abra iniciar.bat.
:fim
pause
