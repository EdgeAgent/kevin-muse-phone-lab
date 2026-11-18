#!/usr/bin/env python3
"""Optional real Android Emulator / ADB backend for PhoneOps.

This adapter does not fake an Android device. It detects the user's Android SDK,
launches real AVDs, installs APKs, runs scoped ADB shell commands, and captures
screenshots. It is intentionally opt-in: the existing local worker simulator
continues to work when Android SDK tools are unavailable.
"""
from __future__ import annotations
import os, shutil, subprocess, time
from pathlib import Path

class AndroidBackendError(RuntimeError): pass

class AndroidBackend:
    def __init__(self):
        sdk = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
        self.sdk = Path(sdk).expanduser() if sdk else None
        self.processes = {}
        self.emulator = self._find("emulator")
        self.adb = self._find("adb", prefer_platform_tools=True)

    def _find(self, name, prefer_platform_tools=False):
        candidates = []
        if self.sdk:
            if prefer_platform_tools: candidates.append(self.sdk / "platform-tools" / (name + (".exe" if os.name == "nt" else "")))
            candidates.append(self.sdk / "emulator" / (name + (".exe" if os.name == "nt" else "")))
        found = shutil.which(name)
        if found: candidates.append(Path(found))
        for candidate in candidates:
            if candidate and candidate.exists(): return str(candidate)
        return None

    @property
    def available(self): return bool(self.emulator and self.adb)

    def _require(self):
        if not self.available:
            raise AndroidBackendError("Android SDK tools not found. Install Android Studio, set ANDROID_HOME, and add emulator/platform-tools to PATH.")

    def _run(self, args, timeout=30, check=True, capture=True):
        result = subprocess.run(args, capture_output=capture, text=True, timeout=timeout)
        if check and result.returncode:
            raise AndroidBackendError((result.stderr or result.stdout or "command failed").strip())
        return result

    def status(self):
        return {"available": self.available, "sdk": str(self.sdk) if self.sdk else None, "emulator": self.emulator, "adb": self.adb, "avds": self.list_avds() if self.available else [], "devices": self.devices() if self.available else []}

    def list_avds(self):
        self._require()
        result = self._run([self.emulator, "-list-avds"])
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    def devices(self):
        self._require()
        result = self._run([self.adb, "devices", "-l"])
        devices = []
        for line in result.stdout.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[1] in {"device", "offline", "unauthorized"}:
                devices.append({"serial": parts[0], "state": parts[1], "details": " ".join(parts[2:])})
        return devices

    def launch(self, avd, port=None, headless=False):
        self._require()
        if avd not in self.list_avds(): raise AndroidBackendError(f"Unknown AVD: {avd}")
        if avd in self.processes and self.processes[avd].poll() is None: return {"avd": avd, "pid": self.processes[avd].pid, "alreadyRunning": True}
        args = [self.emulator, "@" + avd, "-no-boot-anim", "-gpu", "auto"]
        if port: args += ["-port", str(int(port))]
        if headless: args += ["-no-window"]
        log = open(Path(os.environ.get("PHONEOPS_ANDROID_LOG_DIR", ".")) / f"{avd}.emulator.log", "a", encoding="utf-8")
        proc = subprocess.Popen(args, stdout=log, stderr=subprocess.STDOUT, text=True)
        self.processes[avd] = proc
        return {"avd": avd, "pid": proc.pid, "alreadyRunning": False}

    def stop(self, serial):
        self._require()
        self._run([self.adb, "-s", serial, "emu", "kill"], timeout=15)
        for avd, proc in list(self.processes.items()):
            if proc.poll() is not None: self.processes.pop(avd, None)
        return {"serial": serial, "stopped": True}

    def wait_boot(self, serial, timeout=120):
        self._require(); end = time.time() + timeout
        while time.time() < end:
            result = self._run([self.adb, "-s", serial, "shell", "getprop", "sys.boot_completed"], timeout=10, check=False)
            if result.stdout.strip() == "1": return True
            time.sleep(2)
        return False

    def install_apk(self, serial, apk_path):
        self._require(); apk = str(Path(apk_path).expanduser().resolve())
        if not Path(apk).is_file() or Path(apk).suffix.lower() != ".apk": raise AndroidBackendError("Only an existing .apk file may be installed")
        result = self._run([self.adb, "-s", serial, "install", "-r", apk], timeout=180)
        return {"serial": serial, "apk": apk, "output": result.stdout.strip()}

    def shell(self, serial, args):
        self._require()
        if not isinstance(args, list) or not args or any(not isinstance(x, str) for x in args): raise AndroidBackendError("shell args must be a non-empty string list")
        blocked = {"rm", "reboot", "shutdown", "su", "pm", "svc"}
        if args[0] in blocked: raise AndroidBackendError(f"Blocked shell command: {args[0]}")
        result = self._run([self.adb, "-s", serial, "shell", *args], timeout=60)
        return {"serial": serial, "stdout": result.stdout, "stderr": result.stderr}

    def screenshot(self, serial, output_path):
        self._require(); target = Path(output_path).expanduser().resolve(); target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as out:
            result = subprocess.run([self.adb, "-s", serial, "exec-out", "screencap", "-p"], stdout=out, stderr=subprocess.PIPE, timeout=30)
        if result.returncode: raise AndroidBackendError(result.stderr.decode(errors="replace"))
        return {"serial": serial, "path": str(target), "bytes": target.stat().st_size}

if __name__ == "__main__":
    backend = AndroidBackend()
    print(backend.status())
