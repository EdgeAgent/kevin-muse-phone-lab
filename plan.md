# Kevin’s Muse Phone Lab

## Product shape
A local web dashboard that hosts eight independently taskable virtual phone worker processes under the fleet name **Kevin**. It is intentionally a lightweight emulator rather than a full Android/iOS emulator: the upstream Muse Gadget SDK targets Linux/ESP32 gadgets and exposes commands such as `system.run`, `file.read`, `file.write`, and `device.health`. Each phone has its own OS process, working directory, state directory, stdin task queue, PID, and result files.

## Design
- **Design movement:** dark operations console with soft glass panels and restrained neon telemetry.
- **Core principles:** glanceable fleet state, clear isolation per phone, fast task dispatch, visible execution history.
- **Color philosophy:** graphite and ink backgrounds keep attention on state; mint means healthy/ready; amber means working; coral means failed/attention.
- **Layout paradigm:** asymmetric command center: fleet rail on the left, focused dispatch workspace in the center, live signal rail on the right.
- **Signature elements:** numbered phone silhouettes, glowing status pips, monospaced telemetry labels.
- **Interaction philosophy:** every mutation is explicit and immediately reflected in the activity stream; no hidden automation.
- **Animation:** short springy transitions for task state and subtle scanline shimmer only while a device is working.
- **Typography:** Inter/system sans for UI, IBM Plex Mono for IDs and logs.
- **Brand essence:** a calm control room for running many Muse-enabled virtual phones at once. Personality: precise, capable, transparent.
- **Brand voice:** “Dispatch once. Observe everything.” and “This is a simulator boundary, not a hardware claim.”
- **Wordmark:** Kevin wordmark paired with a small 8-dot fleet mark.
- **Signature brand color:** electric mint `#9ef3c6`.

## Implementation
- `server.py`: dependency-free Python HTTP server, worker lifecycle manager, Ollama bridge, and JSON API for fleet state/task dispatch.
- `phone_worker.py`: one isolated local virtual-phone worker process.
- `public/index.html`: single-page command center UI.
- `public/styles.css`: responsive dark console styling.
- `public/app.js`: rendering, worker controls, task dispatch, and polling.
- `manus-routes.json`: route manifest for the root page.
- `OLLAMA-SETUP.md`: local Ollama and Windows executable instructions.

## Runtime
Run `python3 server.py --port 8787`, then open `http://localhost:8787`. On startup the host spawns eight child processes and creates `.kevin-runtime/kevin-XX/` state directories. The dashboard exposes Start worker and Stop controls for each phone. Tasks are queued over stdin and produce command-shaped activity records. When Ollama Desktop is running, the Ask Kevin panel sends a structured planning request to the local model and validates its selected phone and task before dispatch. Windows users can build `kevin-server.exe` and `kevin-phone-worker.exe` with `build-kevin-exe.ps1`.
