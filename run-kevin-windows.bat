@echo off
setlocal
cd /d "%~dp0"
set OLLAMA_URL=http://localhost:11434
if "%OLLAMA_MODEL%"=="" set OLLAMA_MODEL=llama3.2
if exist "kevin-phone-worker.exe" set KEVIN_WORKER_EXE=%~dp0kevin-phone-worker.exe
start "Kevin Muse Phone Lab" /min kevin-server.exe --port 8787
 timeout /t 2 /nobreak >nul
start "" http://localhost:8787
endlocal
