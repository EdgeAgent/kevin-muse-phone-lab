# Real Android Emulator Mode

PhoneOps now includes an optional Android Emulator / ADB backend. This is the path for actual Android environments with a real Android OS, installed APKs, app data, shell access, screenshots, and screen recordings. The existing Python workers remain available as a lightweight fallback when Android SDK tools are not installed.

## What changes in real mode

Each Android slot is backed by an Android Virtual Device (AVD), not a Python process pretending to be a phone. The Android Emulator preserves app and user-data state in the AVD data partition. PhoneOps can discover AVDs, launch or stop them, list ADB devices, install APKs, run a restricted shell command, and capture a PNG screen image.

The official Android command-line flow is `emulator @avd_name`, followed by ADB operations. Android documents `emulator -list-avds`, `-no-window` for headless operation, and host acceleration through KVM on Linux or WHPX on Windows. See the [Android Emulator command-line reference](https://developer.android.com/studio/run/emulator-commandline).

## Windows setup

Install Android Studio and Android SDK components. In SDK Manager, install:

- Android Emulator
- Android SDK Platform-Tools
- One x86_64 system image, preferably a Google APIs or Google Play image
- A platform matching that system image

Set the SDK path in PowerShell if Android Studio did not set it globally:

```powershell
$env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
$env:Path += ";$env:ANDROID_HOME\emulator;$env:ANDROID_HOME\platform-tools"

emulator -accel-check
adb version
emulator -list-avds
```

Create an AVD in Android Studio’s Device Manager. For a fleet, create names such as:

```text
PhoneOps-01
PhoneOps-02
PhoneOps-03
PhoneOps-04
PhoneOps-05
PhoneOps-06
PhoneOps-07
PhoneOps-08
```

Eight full Android instances can require substantial RAM, CPU, disk, and GPU resources. Start with one or two AVDs, measure the host, and scale toward eight only when the machine remains responsive.

## Start and inspect real devices

Start one AVD directly:

```powershell
emulator @PhoneOps-01 -no-boot-anim
adb devices -l
```

For a server without a desktop window:

```powershell
emulator @PhoneOps-01 -no-window -no-boot-anim
```

Check PhoneOps’ Android backend:

```powershell
Invoke-RestMethod http://localhost:8787/api/android/status | ConvertTo-Json -Depth 8
```

The result reports whether Android tools are available, discovered AVDs, and connected ADB serials.

## Install real apps

Install an APK on a selected emulator:

```powershell
adb -s emulator-5554 install -r .\downloads\my-app.apk
```

PhoneOps exposes the same operation through:

```powershell
Invoke-RestMethod http://localhost:8787/api/android/install `
  -Method Post `
  -ContentType 'application/json' `
  -Body '{"serial":"emulator-5554","apk":"C:\\Users\\you\\Downloads\\my-app.apk"}'
```

For Play Store applications, use an AVD system image that includes Google Play and complete the normal user setup inside the emulator. PhoneOps does not bypass licensing, account authentication, paid-app restrictions, CAPTCHAs, or app security controls.

## Screen access and automation

Capture a real emulator screen:

```powershell
adb -s emulator-5554 exec-out screencap -p > phoneops-screen.png
```

PhoneOps exposes the same capture operation through `/api/android/screenshot`. A future dashboard panel can stream these images or use a WebRTC companion for live mirroring. Android also provides `screenrecord` for short recordings.

The backend supports a restricted shell endpoint for safe inspection. Destructive operations such as reboot, package-manager changes, service changes, and privilege escalation are blocked by default. A production agent should add per-command allowlists and human approval for consequential actions.

## PhoneOps API surface

```text
GET  /api/android/status
POST /api/android/launch       { avd, port?, headless? }
POST /api/android/stop         { serial }
POST /api/android/install      { serial, apk }
POST /api/android/shell        { serial, args[] }
POST /api/android/screenshot   { serial }
```

The current API adapter is intentionally opt-in. If Android SDK tools are not available, PhoneOps continues using its eight lightweight local workers and reports Android as unavailable rather than claiming that a simulator is a full emulator.

## Production direction

The next production layer is an Android slot manager that maps each PhoneOps lane to an AVD, waits for `sys.boot_completed`, starts an agent runner inside the selected AVD, and sends live frames to the dashboard. Appium or a similarly scoped automation layer can be added for semantic UI actions, while ADB remains the installation and low-level device channel.
