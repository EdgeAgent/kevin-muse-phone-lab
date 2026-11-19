@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Setup-PhoneOps-GooglePlay.ps1"
if errorlevel 1 (
  echo.
  echo Google Play AVD setup did not complete. Review the message above.
  pause
)
endlocal
