@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  python -m venv .venv
) else (
  py -3 -m venv .venv
)
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo Setup complete. Open RUN.bat to start LPHK.
pause
exit /b 0
:failed
echo Setup failed. Install Python 3.11 or 3.12 with Tcl/Tk and pip, then try again.
pause
exit /b 1
