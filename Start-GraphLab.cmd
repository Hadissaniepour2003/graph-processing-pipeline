@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel% equ 0 (
  set "GRAPH_PYTHON=py -3"
) else (
  set "GRAPH_PYTHON=python"
)
%GRAPH_PYTHON% -c "import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)" >nul 2>nul
if errorlevel 1 (
  echo Install Python 3.12 or newer from https://www.python.org/downloads/windows/
  echo Tick "Add python.exe to PATH" in the installer, then reopen this file.
  pause
  exit /b 1
)
if not exist .venv\Scripts\python.exe (
  echo Creating the project's Python environment...
  %GRAPH_PYTHON% -m venv .venv
  if errorlevel 1 goto failed
)
echo Checking project dependencies. The first launch needs internet access...
.venv\Scripts\python.exe -m pip install -r requirements.txt --disable-pip-version-check
if errorlevel 1 goto failed
.venv\Scripts\python.exe run_lab.py %*
if errorlevel 1 goto failed
exit /b 0
:failed
echo.
echo Graph Lab could not start. Read the error above and keep this window open.
pause
exit /b 1
