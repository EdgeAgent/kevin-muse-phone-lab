# Test Kevin locally on Windows

## 1. Start Kevin

After building the executables, run `run-kevin-windows.bat`. It starts `kevin-server.exe`, launches eight `kevin-phone-worker.exe` processes, and opens the dashboard at `http://localhost:8787`.

You can confirm the server from PowerShell:

```powershell
Invoke-WebRequest http://localhost:8787/ | Select-Object StatusCode
Invoke-RestMethod http://localhost:8787/api/state | ConvertTo-Json -Depth 6
Invoke-RestMethod http://localhost:8787/api/ollama/status | ConvertTo-Json
```

The state response should show `fleet: Kevin`, eight phones, and a numeric `workerPid` for each online worker.

## 2. Run the included smoke test

With Kevin running, execute:

```powershell
python .\test_kevin.py
```

A successful run prints that eight workers are online, dispatches a health scan to `kevin-01`, runs a second health scan across all eight workers in parallel, confirms completion, and reports Ollama connectivity.

## 3. Configure local Ollama models

Ollama models are selected with `OLLAMA_MODEL`. Pull the models you want:

```powershell
ollama pull llama3.2
ollama pull mistral
ollama pull deepseek-r1:7b
ollama list
```

Run Kevin with Mistral:

```powershell
$env:OLLAMA_MODEL = "mistral"
.\run-kevin-windows.bat
```

Run Kevin with DeepSeek:

```powershell
$env:OLLAMA_MODEL = "deepseek-r1:7b"
.\run-kevin-windows.bat
```

Kevin sends a non-streaming structured JSON request to Ollama. The model must return a phone ID, a supported task preset, and a reason. Kevin rejects unknown phones and unsupported tasks before anything reaches a worker.

## 4. Check worker status and logs

The dashboard shows each worker’s current state and PID. The API gives the same information:

```powershell
$state = Invoke-RestMethod http://localhost:8787/api/state
$state.phones | Select-Object id,name,status,power,workerPid,stateDir,lastTask | Format-Table
```

Each phone writes local state under:

```text
.kevin-runtime\kevin-01\
.kevin-runtime\kevin-02\
...
.kevin-runtime\kevin-08\
```

Inside each directory, `phone-state.json` records the worker identity and `last-result.json` records the most recent completed command. The server’s event stream is available in the dashboard and in each phone’s `events` array:

```powershell
$state.phones | ForEach-Object { "[$($_.id)]"; $_.events }
```

To dispatch a workflow to every ready worker from PowerShell:

```powershell
Invoke-RestMethod http://localhost:8787/api/parallel/dispatch -Method Post -ContentType 'application/json' -Body '{"preset":"health-scan"}' | ConvertTo-Json -Depth 6
```

For a live process view:

```powershell
Get-Process kevin-server,kevin-phone-worker -ErrorAction SilentlyContinue | Select-Object Id,ProcessName,StartTime
```

To stop Kevin, close the server console or run:

```powershell
Get-Process kevin-server,kevin-phone-worker -ErrorAction SilentlyContinue | Stop-Process
```

If Ollama shows `offline`, check that Ollama Desktop is running, then test:

```powershell
Invoke-RestMethod http://localhost:11434/api/tags | ConvertTo-Json
```
