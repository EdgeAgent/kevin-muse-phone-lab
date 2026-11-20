#!/usr/bin/env python3
"""Kevin's Muse Phone Lab: local multi-process virtual phone host."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import argparse, json, os, subprocess, threading, time, uuid, sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from android_backend import AndroidBackend, AndroidBackendError
from browser_backend import BrowserBackend

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
SOURCE_ROOT = Path(__file__).parent
RUNTIME = ROOT / ".kevin-runtime"
PHONE_NAMES = ["Atlas", "Beacon", "Cedar", "Delta", "Echo", "Fable", "Grove", "Halo"]
DEFAULT_APPS = [
    {"name":"Chrome","package":"com.android.chrome","kind":"browser"},
    {"name":"Phone","package":"com.google.android.dialer","kind":"system"},
    {"name":"Messages","package":"com.google.android.apps.messaging","kind":"messaging"},
    {"name":"Contacts","package":"com.google.android.contacts","kind":"contacts"},
    {"name":"Calendar","package":"com.google.android.calendar","kind":"calendar"},
    {"name":"Camera","package":"com.google.android.GoogleCamera","kind":"camera"},
    {"name":"Files","package":"com.google.android.documentsui","kind":"files"},
    {"name":"Settings","package":"com.android.settings","kind":"system"},
    {"name":"Play Store","package":"com.android.vending","kind":"store"},
]
TASK_PRESETS = {
    "check-inbox": ("Check inbox", "Review unread messages and summarize anything urgent.", 3.4, "system.run"),
    "capture-screen": ("Capture screen", "Capture the current screen and attach it to the activity log.", 2.3, "file.write"),
    "health-scan": ("Health scan", "Collect battery, storage, network, and app health signals.", 2.0, "device.health"),
    "open-calendar": ("Open calendar", "Open the calendar app and surface the next appointment.", 2.7, "system.run"),
    "draft-reply": ("Draft a reply", "Draft a concise reply to the latest conversation; do not send.", 4.0, "system.run"),
}
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")
REMOTE_PUBLIC_URL = os.environ.get("REMOTE_PUBLIC_URL", "http://localhost:8787")

def now(): return time.strftime("%H:%M:%S")

def make_phone(index):
    return {"id": f"kevin-{index+1:02d}", "name": PHONE_NAMES[index], "slot": index + 1,
            "status": "ready", "power": "on", "battery": 92 - index * 4, "signal": 4 - (index % 2),
            "network": "Wi-Fi 6", "app": "Chrome", "apps": [dict(app, installed=True, source="starter-pack") for app in DEFAULT_APPS], "lastTask": "No task dispatched", "updated": now(),
            "workerPid": None, "stateDir": str(RUNTIME / f"kevin-{index+1:02d}"),
            "events": [{"time": now(), "kind": "system", "text": "Virtual device waiting to spawn"}]}

phones = {p["id"]: p for p in [make_phone(i) for i in range(8)]}
workers = {}
remote_links = {}
android = AndroidBackend()
browser = BrowserBackend(RUNTIME)
lock = threading.Lock()

def public_state():
    with lock:
        snapshot = list(phones.values())
        for phone in snapshot:
            phone["browser"] = browser.status(phone["id"])
        return {"fleet": "PhoneOps", "phones": snapshot, "presets": {k: {"label": v[0], "description": v[1]} for k, v in TASK_PRESETS.items()}}

def add_event(phone, event):
    phone["events"].insert(0, event); phone["events"] = phone["events"][:8]; phone["updated"] = now()

def worker_reader(phone_id, proc):
    for line in proc.stdout:
        try: event = json.loads(line)
        except json.JSONDecodeError: continue
        with lock:
            phone = phones.get(phone_id)
            if not phone: continue
            if event["type"] == "started":
                phone["status"] = "working"; phone["lastTask"] = event["label"]
                add_event(phone, {"time": now(), "kind": "dispatch", "text": f"{event['label']} dispatched", "taskId": event["taskId"], "command": event["command"]})
            elif event["type"] == "completed":
                phone["status"] = "ready"; phone["app"] = event.get("app", phone["app"])
                add_event(phone, {"time": now(), "kind": "success", "text": f"{event['label']} completed", "taskId": event["taskId"], "command": event["command"]})
    with lock:
        phone = phones.get(phone_id)
        if phone:
            phone["workerPid"] = None; phone["power"] = "off"; phone["status"] = "offline"
            add_event(phone, {"time": now(), "kind": "system", "text": "Virtual device stopped"})
        workers.pop(phone_id, None)

def spawn_worker(phone_id):
    with lock:
        if phone_id in workers and workers[phone_id].poll() is None: return
        phone = phones[phone_id]; phone_dir = Path(phone["stateDir"]); phone_dir.mkdir(parents=True, exist_ok=True)
        worker_exe = os.environ.get("KEVIN_WORKER_EXE")
        command = [worker_exe] if worker_exe else [sys.executable, str(SOURCE_ROOT / "phone_worker.py")]
        proc = subprocess.Popen(command + ["--phone-id", phone_id, "--name", phone["name"], "--state-dir", str(phone_dir)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1)
        workers[phone_id] = proc; phone["workerPid"] = proc.pid; phone["power"] = "on"; phone["status"] = "ready"
        add_event(phone, {"time": now(), "kind": "system", "text": f"Worker spawned (PID {proc.pid})"})
    threading.Thread(target=worker_reader, args=(phone_id, proc), daemon=True).start()

def stop_worker(phone_id):
    with lock: proc = workers.get(phone_id)
    if proc:
        proc.terminate()
        try: proc.wait(timeout=2)
        except subprocess.TimeoutExpired: proc.kill()
    else:
        with lock:
            phone = phones[phone_id]; phone["power"] = "off"; phone["status"] = "offline"

def dispatch(phone_id, payload):
    key = payload.get("preset"); custom = (payload.get("task") or "").strip()
    if key not in TASK_PRESETS and not custom: raise ValueError("Choose a preset or enter a task")
    if key not in TASK_PRESETS:
        key = "custom-" + uuid.uuid4().hex[:6]; TASK_PRESETS[key] = (custom[:40], custom, 3.0, "system.run")
    with lock:
        phone = phones.get(phone_id); proc = workers.get(phone_id)
        if not phone: raise ValueError("Unknown phone")
        if not proc or proc.poll() is not None: raise ValueError("Phone is offline — start its worker first")
        if phone["status"] == "working": raise ValueError("This phone is already working")
        label, description, delay, command = TASK_PRESETS[key]; task_id = "tsk_" + uuid.uuid4().hex[:8]
        try: proc.stdin.write(json.dumps({"taskId": task_id, "key": key, "label": label, "description": description, "delay": delay, "command": command}) + "\n"); proc.stdin.flush()
        except (BrokenPipeError, AttributeError): raise ValueError("Phone worker is not available")
    return {"taskId": task_id, "phoneId": phone_id, "label": label, "command": command}

def ollama_request(path, payload=None, timeout=45):
    body = None if payload is None else json.dumps(payload).encode()
    req = Request(OLLAMA_URL.rstrip("/") + path, data=body, headers={"Content-Type": "application/json"} if body else {})
    with urlopen(req, timeout=timeout) as response:
        return json.loads(response.read())

def ollama_status():
    try:
        data = ollama_request("/api/tags", timeout=3)
        return {"connected": True, "url": OLLAMA_URL, "model": OLLAMA_MODEL, "models": [m.get("name") for m in data.get("models", [])]}
    except (URLError, HTTPError, TimeoutError, OSError) as exc:
        return {"connected": False, "url": OLLAMA_URL, "model": OLLAMA_MODEL, "error": str(exc)}

def agent_dispatch(instruction):
    snapshot = public_state()
    phone_lines = "\n".join(f"{p['id']} ({p['name']}): status={p['status']}, app={p['app']}, battery={p['battery']}%" for p in snapshot["phones"])
    presets = "\n".join(f"{key}: {value[0]} — {value[1]}" for key, value in TASK_PRESETS.items())
    system = "You are PhoneOps, a local phone fleet operator. Plan exactly one safe task for exactly one virtual phone. Never invent a phone id or preset. Return JSON only with keys phone_id, preset, reason. Use a preset when possible. If the user asks for a task not represented by a preset, use preset custom and put the exact task in reason. Do not claim to have sent messages, accessed accounts, or changed real devices: this is a local simulator."
    user = f"Instruction: {instruction}\n\nAvailable phones:\n{phone_lines}\n\nAvailable presets:\n{presets}"
    payload = {"model": OLLAMA_MODEL, "stream": False, "format": {"type": "object", "properties": {"phone_id": {"type": "string"}, "preset": {"type": "string"}, "reason": {"type": "string"}}, "required": ["phone_id", "preset", "reason"]}, "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
    result = ollama_request("/api/chat", payload)
    plan = json.loads(result.get("message", {}).get("content", "{}"))
    phone_id = plan.get("phone_id"); preset = plan.get("preset")
    if phone_id not in phones: raise ValueError("Ollama selected an unknown phone")
    if preset == "custom":
        task = instruction; preset = None
    elif preset not in TASK_PRESETS:
        raise ValueError("Ollama selected an unavailable preset")
    else:
        task = None
    return {"plan": plan, "dispatch": dispatch(phone_id, {"preset": preset, "task": task}), "model": OLLAMA_MODEL}

def parallel_dispatch(payload):
    phone_ids = payload.get("phone_ids") or list(phones.keys())
    preset = payload.get("preset")
    task = (payload.get("task") or "").strip()
    if not isinstance(phone_ids, list) or not phone_ids: raise ValueError("phone_ids must contain at least one phone")
    if not preset and not task: raise ValueError("preset or task is required")
    results = []
    with ThreadPoolExecutor(max_workers=min(8, len(phone_ids))) as pool:
        futures = {pool.submit(dispatch, phone_id, {"preset": preset, "task": task}): phone_id for phone_id in phone_ids}
        for future in as_completed(futures):
            phone_id = futures[future]
            try: results.append({"ok": True, **future.result()})
            except Exception as exc: results.append({"ok": False, "phoneId": phone_id, "error": str(exc)})
    return {"requested": len(phone_ids), "dispatched": sum(1 for r in results if r["ok"]), "results": sorted(results, key=lambda r: r.get("phoneId", ""))}

def create_remote_link(phone_id):
    with lock:
        if phone_id not in phones: raise ValueError("Unknown phone")
        token = uuid.uuid4().hex
        remote_links[token] = {"phoneId": phone_id, "createdAt": time.time(), "expiresAt": time.time() + 900, "connected": False, "deviceName": None}
        add_event(phones[phone_id], {"time": now(), "kind": "system", "text": "Remote pairing link created (expires in 15 min)"})
        return {"phoneId": phone_id, "token": token, "url": f"{REMOTE_PUBLIC_URL.rstrip('/')}/remote/{token}", "expiresInSeconds": 900}

def remote_status():
    with lock:
        cutoff = time.time()
        for token in list(remote_links):
            if remote_links[token]["expiresAt"] < cutoff: del remote_links[token]
        return [{"token": token, **link} for token, link in remote_links.items()]

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass
    def send_json(self, code, data):
        raw=json.dumps(data).encode(); self.send_response(code); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(raw))); self.send_header("Cache-Control","no-store"); self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        path=urlparse(self.path).path
        if path=="/api/state": return self.send_json(200, public_state())
        if path=="/api/ollama/status": return self.send_json(200, ollama_status())
        if path=="/api/remote/status": return self.send_json(200, {"ok": True, "links": remote_status()})
        if path=="/api/android/status": return self.send_json(200, {"ok": True, "android": android.status()})
        if path=="/api/browser/status": return self.send_json(200, {"ok": True, "browsers": browser.status()})
        if path.startswith("/remote/"):
            token = path.split("/", 2)[2]
            with lock: link = remote_links.get(token)
            if not link or link["expiresAt"] < time.time(): return self.send_json(404, {"ok": False, "error": "Pairing link is invalid or expired"})
            return self.send_json(200, {"ok": True, "message": "PhoneOps pairing link is ready for a trusted phone-side companion.", "phoneId": link["phoneId"], "expiresAt": link["expiresAt"], "next": "POST /api/remote/connect with token and device_name"})
        if path=="/manus-routes.json": return self.send_json(200,{"routes":[{"path":"/","title":"Kevin’s Muse Phone Lab"}]})
        target=ROOT/"public"/("index.html" if path=="/" else path.lstrip("/"))
        if target.is_file():
            data=target.read_bytes(); typ="text/html" if target.suffix==".html" else "text/css" if target.suffix==".css" else "application/javascript"; self.send_response(200); self.send_header("Content-Type",typ); self.send_header("Content-Length",str(len(data))); self.end_headers(); self.wfile.write(data); return
        self.send_json(404,{"error":"not found"})
    def do_POST(self):
        path=urlparse(self.path).path; parts=path.strip("/").split("/")
        try:
            length=int(self.headers.get("Content-Length",0)); payload=json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError: return self.send_json(400,{"ok":False,"error":"invalid JSON"})
        try:
            if len(parts)==4 and parts[:2]==["api","phones"] and parts[3]=="tasks": return self.send_json(200,{"ok":True,"dispatch":dispatch(parts[2],payload)})
            if len(parts)==4 and parts[:2]==["api","phones"] and parts[3]=="power":
                if payload.get("action")=="start": spawn_worker(parts[2])
                elif payload.get("action")=="stop": stop_worker(parts[2])
                else: raise ValueError("action must be start or stop")
                return self.send_json(200,{"ok":True})
            if path == "/api/agent/dispatch":
                instruction = str(payload.get("instruction", "")).strip()
                if not instruction: raise ValueError("instruction is required")
                return self.send_json(200, {"ok": True, "agent": agent_dispatch(instruction)})
            if path == "/api/parallel/dispatch":
                return self.send_json(200, {"ok": True, "parallel": parallel_dispatch(payload)})
            if len(parts)==5 and parts[:2]==["api","phones"] and parts[3]=="browser" and parts[4] in ("navigate", "search"):
                phone_id = parts[2]
                if phone_id not in phones: raise ValueError("Unknown phone")
                if parts[4] == "navigate":
                    result = browser.navigate(phone_id, payload.get("url"))
                else:
                    result = browser.search(phone_id, payload.get("query"), payload.get("engine", "duckduckgo"))
                with lock:
                    phones[phone_id]["app"] = "Chrome"
                    phones[phone_id]["browser"] = result
                    add_event(phones[phone_id], {"time": now(), "kind": "web", "text": f"Browser {parts[4]}: {result.get('title') or result.get('url')}"})
                return self.send_json(200, {"ok": True, "phoneId": phone_id, "browser": result})
            if len(parts)==5 and parts[:2]==["api","phones"] and parts[3]=="browser" and parts[4]=="screenshot":
                phone_id = parts[2]
                if phone_id not in phones: raise ValueError("Unknown phone")
                return self.send_json(200, {"ok": True, "phoneId": phone_id, "browser": browser.screenshot(phone_id)})
            if path == "/api/remote/link":
                return self.send_json(200, {"ok": True, "link": create_remote_link(str(payload.get("phone_id", "")))})
            if path == "/api/remote/connect":
                token = str(payload.get("token", ""))
                with lock:
                    link = remote_links.get(token)
                    if not link or link["expiresAt"] < time.time(): raise ValueError("Pairing link is invalid or expired")
                    link["connected"] = True; link["deviceName"] = str(payload.get("device_name", "Remote phone"))[:80]
                    phones[link["phoneId"]]["power"] = "linked"; phones[link["phoneId"]]["status"] = "linked"
                    add_event(phones[link["phoneId"]], {"time": now(), "kind": "system", "text": f"Remote phone linked: {link['deviceName']}"})
                return self.send_json(200, {"ok": True, "phoneId": link["phoneId"]})
            if path == "/api/remote/status":
                return self.send_json(200, {"ok": True, "links": remote_status()})
            if path == "/api/android/launch":
                return self.send_json(200, {"ok": True, "android": android.launch(str(payload.get("avd", "")), payload.get("port"), bool(payload.get("headless", False)))})
            if path == "/api/android/stop":
                return self.send_json(200, {"ok": True, "android": android.stop(str(payload.get("serial", "")))})
            if path == "/api/android/install":
                return self.send_json(200, {"ok": True, "android": android.install_apk(str(payload.get("serial", "")), str(payload.get("apk", "")))})
            if path == "/api/android/shell":
                return self.send_json(200, {"ok": True, "android": android.shell(str(payload.get("serial", "")), payload.get("args"))})
            if path == "/api/android/screenshot":
                serial = str(payload.get("serial", "")); safe = "".join(c for c in serial if c.isalnum() or c in "-_") or "device"
                output = str((RUNTIME / "android-screens" / f"{safe}.png").resolve())
                return self.send_json(200, {"ok": True, "android": android.screenshot(serial, output)})
        except (ValueError, KeyError, json.JSONDecodeError, URLError, HTTPError, TimeoutError, OSError, AndroidBackendError) as exc: return self.send_json(400,{"ok":False,"error":str(exc)})
        self.send_json(404,{"error":"not found"})

if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--port",type=int,default=8787); args=parser.parse_args(); RUNTIME.mkdir(exist_ok=True)
    for phone_id in phones: spawn_worker(phone_id)
    print(f"Kevin Muse Phone Lab listening on http://0.0.0.0:{args.port} with {len(phones)} worker processes")
    try: ThreadingHTTPServer(("0.0.0.0",args.port),Handler).serve_forever()
    finally:
        for phone_id in list(workers): stop_worker(phone_id)
        browser.close()
