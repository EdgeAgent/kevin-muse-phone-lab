# Kevin + Ollama local agent

Kevin connects to the Ollama Desktop app through its local HTTP API at `http://localhost:11434`. Ollama must be installed and running on the same computer as Kevin. The default model is `llama3.2`; change it with `OLLAMA_MODEL`.

On Windows, install Ollama Desktop, then open PowerShell in this folder and download a local model:

```powershell
ollama pull llama3.2
$env:OLLAMA_MODEL = "llama3.2"
.\run-kevin-windows.bat
```

The dashboard’s **Ask Kevin** box sends your instruction to the local model. The model can only choose from Kevin’s eight phone IDs and the safe preset task list. Kevin validates the returned JSON before dispatching it to a worker. The agent does not send messages, access accounts, or control real devices.

To build native Windows executables, run PowerShell as a normal user from this folder:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build-kevin-exe.ps1
.\run-kevin-windows.bat
```

This produces `kevin-server.exe` and `kevin-phone-worker.exe`. The batch launcher sets `KEVIN_WORKER_EXE` automatically. For a different model:

```powershell
$env:OLLAMA_MODEL = "qwen2.5:7b"
.\run-kevin-windows.bat
```

Ollama’s official Windows documentation says the app runs in the background and serves its API at `http://localhost:11434`. Its chat API supports non-streaming responses and structured JSON output, which Kevin uses to keep agent decisions inside the allowed phone/task boundary.
