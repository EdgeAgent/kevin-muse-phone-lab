@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1
if errorlevel 1 (
  echo Python 3 was not found. Install Python from https://www.python.org/downloads/windows/ and run this again.
  pause
  exit /b 1
)
echo Installing the PhoneOps per-phone browser bridge...
py -m pip install --upgrade playwright
if errorlevel 1 goto :failed
py -m playwright install chromium
if errorlevel 1 goto :failed
echo Browser support is ready. Launching PhoneOps...
call "%~dp0Start-PhoneOps.bat"
exit /b 0
:failed
echo Browser setup failed. Review the message above and try again.
pause
exit /b 1
