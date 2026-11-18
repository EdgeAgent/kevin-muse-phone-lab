# PhoneOps — by EDGE | AGENCY

## Product shape
PhoneOps is a local phone-agent operations console with two execution backends:

1. **Real Android mode:** Android Studio Emulator / AVD instances with installed apps, persistent app data, ADB commands, APK installation, and screenshots.
2. **Safe fallback mode:** lightweight isolated worker processes for environments without Android SDK tools.

The operator can choose a phone lane, ask the local Ollama model for an approved plan, dispatch the same workflow in parallel, inspect execution history, or use the Remote Phone Link scaffold for a future real-phone companion.

## Real Android architecture

- `android_backend.py`: discovers Android SDK tools, lists AVDs and ADB devices, launches/stops AVDs, installs APKs, captures screenshots, and exposes a restricted shell.
- `server.py`: hosts the PhoneOps dashboard, worker lifecycle, Ollama bridge, parallel dispatch, remote pairing, and Android API routes.
- `phone_worker.py`: safe local fallback worker used when Android SDK tools are unavailable.
- `ANDROID-EMULATOR.md`: setup, AVD fleet guidance, APK installation, screen capture, and production direction.

## Real Android API

- `GET /api/android/status`
- `POST /api/android/launch`
- `POST /api/android/stop`
- `POST /api/android/install`
- `POST /api/android/shell`
- `POST /api/android/screenshot`

## Production roadmap

1. Validate one Android AVD end-to-end on the operator’s Windows machine.
2. Add an AVD slot manager that maps PhoneOps lanes to emulator serials.
3. Wait for Android boot completion before dispatching tasks.
4. Add an Appium/UIAutomator action layer with per-action allowlists.
5. Add live screen streaming to the dashboard.
6. Add isolated profiles, test-account boundaries, audit logs, and explicit approvals.
7. Scale from one AVD to two, then measure the host before attempting eight.

Eight full Android emulators are materially heavier than eight Python workers. The machine needs hardware acceleration, adequate RAM, CPU, disk, and GPU resources. PhoneOps should scale gradually rather than silently launching eight resource-heavy instances.
