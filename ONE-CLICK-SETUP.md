# One-click PhoneOps setup

## For normal Windows users

1. Download or clone this repository.
2. Double-click `Install-PhoneOps.bat`.
3. The installer creates a desktop shortcut named **PhoneOps**.
4. Double-click the shortcut to start PhoneOps and open `http://localhost:8787`.

The installer prefers the packaged `kevin-server.exe` and `kevin-phone-worker.exe`, so normal users do not need Python. If the EXEs are not present, it can build them from source when Python is installed.

## Android mode

The installer checks for Android Studio. If it is missing and Windows Package Manager is available, it offers to install Android Studio. Android Studio still needs to be opened once so the user can accept Google’s SDK license terms and install the Android Emulator, Platform-Tools, and at least one system image.

That license step cannot be silently bypassed. After creating an AVD such as `PhoneOps-01`, PhoneOps can detect it through the Android backend.

## If Windows blocks the script

Right-click `Install-PhoneOps.bat` and choose **Run as administrator** only if Windows requests permission to install prerequisites. PhoneOps itself runs locally and does not require administrator access after setup.

## What “one click” includes

- Prerequisite detection
- Optional Python installation through `winget`
- Optional Android Studio installation through `winget`
- Source build fallback when packaged EXEs are absent
- Desktop shortcut creation
- Local `downloads` and `logs` folders
- Browser launch to the PhoneOps dashboard
- Safe fallback to lightweight workers when Android SDK tools are not installed
