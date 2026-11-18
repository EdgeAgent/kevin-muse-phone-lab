@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-PhoneOps.ps1"
if errorlevel 1 (
  echo.
  echo PhoneOps setup did not complete. Review the message above.
  pause
)
endlocal
