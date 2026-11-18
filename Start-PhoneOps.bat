@echo off
setlocal
cd /d "%~dp0"
set OLLAMA_URL=http://localhost:11434
if "%OLLAMA_MODEL%"=="" set OLLAMA_MODEL=llama3.2
if exist "%~dp0kevin-phone-worker.exe" set KEVIN_WORKER_EXE=%~dp0kevin-phone-worker.exe
if exist "%~dp0kevin-server.exe" (
  start "PhoneOps — by EDGE | AGENCY" /min "%~dp0kevin-server.exe" --port 8787
) else (
  where py >nul 2>&1
  if not errorlevel 1 (
    start "PhoneOps — by EDGE | AGENCY" /min py "%~dp0server.py" --port 8787
  ) else (
    start "PhoneOps — by EDGE | AGENCY" /min python "%~dp0server.py" --port 8787
  )
)
timeout /t 3 /nobreak >nul
start "" http://localhost:8787
endlocal
