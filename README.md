# PhoneOps — by EDGE | AGENCY

PhoneOps is a professional local agent operations console for eight independently taskable virtual phone workers. It connects to Ollama Desktop on the same computer, validates structured decisions, and dispatches work to one phone or to multiple phones in parallel.

The workers are lightweight virtual environments with private state directories, process IDs, task queues, and execution events. They are not full Android or iOS emulators and do not access real accounts or send real messages.

![EDGE | AGENCY dashboard](docs/screenshots/kevin-dashboard.webp)

## Why EDGE | AGENCY

PhoneOps is designed as a local control plane for repeatable, observable agent workflows. A human can dispatch a task manually, ask the local model to select the appropriate phone, or run an approved workflow across every ready phone simultaneously. Every decision is validated before execution and every worker reports its status back to the console.

## Best use cases and prompts

**Inbox triage across a team of simulated phones**

> “Have three available phones review their inbox state. Assign one to identify urgent items, one to summarize routine messages, and one to flag messages that need a human reply. Do not send anything.”

**Parallel QA and regression checks**

> “Run a health scan on every ready phone in parallel. Report which workers completed successfully and identify any offline or working devices.”

**Calendar and appointment preparation**

> “Have the next available phone open the calendar and surface the next appointment. Do not modify or cancel anything.”

**Content review and moderation preparation**

> “Assign separate phones to review the pending content queue, capture a screen for audit evidence, and draft a non-sending moderation summary.”

**Fleet readiness checks**

> “Run the health scan across all eight phones in parallel, then summarize readiness by worker ID, process ID, battery, and last completed task.”

**Drafting without sending**

> “Use one ready phone to draft a concise reply to the latest conversation. Do not send the reply or access any external account.”

These prompts are deliberately written with clear scope, no-send boundaries, and observable outcomes. The current preset library supports health scans, inbox review, screen capture, calendar opening, and reply drafting.

## Quick start on Windows

Install Ollama Desktop, then pull a local model:

```powershell
ollama pull llama3.2
```

Build the local executables:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build-kevin-exe.ps1
.\run-kevin-windows.bat
```

Open `http://localhost:8787`. Use **Ask Kevin** for natural-language control or **Run in parallel** to dispatch one approved workflow to all ready phones.

## Configure local models

```powershell
ollama pull mistral
$env:OLLAMA_MODEL = "mistral"
.\run-kevin-windows.bat

ollama pull deepseek-r1:7b
$env:OLLAMA_MODEL = "deepseek-r1:7b"
.\run-kevin-windows.bat
```

The model is called through Ollama’s local API at `http://localhost:11434`. See [OLLAMA-SETUP.md](OLLAMA-SETUP.md) for configuration details.

## Test and inspect

With EDGE | AGENCY running:

```powershell
python .\test_kevin.py
Invoke-RestMethod http://localhost:8787/api/state | ConvertTo-Json -Depth 6
Invoke-RestMethod http://localhost:8787/api/ollama/status | ConvertTo-Json
```

Read [LOCAL-TESTING.md](LOCAL-TESTING.md) for worker status, state files, process inspection, parallel dispatch, and log checks.

## Safety boundary

The local agent can only select PhoneOps’ eight phone IDs and supported task presets. The server validates model output before dispatch. Parallel execution is bounded to the eight local workers. The system does not send messages, access accounts, or control real devices.
