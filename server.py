#!/usr/bin/env python3
"""Kevin's Muse Phone Lab: local multi-process virtual phone host."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
import argparse, json, os, subprocess, threading, time, uuid, sys
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
SOURCE_ROOT = Path(__file__).parent
RUNTIME = ROOT / ".kevin-runtime"
PHONE_NAMES = ["Atlas", "Beacon", "Cedar", "Delta", "Echo", "Fable", "Grove", "Halo"]
TASK_PRESETS = {
    "check-inbox": ("Check inbox", "Review unread messages and summarize anything urgent.", 3.4, "system.run"),
    "capture-screen": ("Capture screen", "Capture the current screen and attach it to the activity log.", 2.3, "file.write"),
    "health-scan": ("Health scan", "Collect battery, storage, network, and app health signals.", 2.0, "device.health"),
    "open-calendar": ("Open calendar", "Open the calendar app and surface the next appointment.", 2.7, "system.run"),
    "draft-reply": ("Draft a reply", "Draft a concise reply to the latest conversation; do not send.", 4.0, "system.run"),
}
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")

def now(): return time.strftime("%H:%M:%S")

def make_phone(index):
    return {"id": f"kevin-{index+1:02d}", "name": PHONE_NAMES[index], "slot": index + 1,
            "status": "ready", "power": "on", "battery": 92 - index * 4, "signal": 4 - (index % 2),
            "network": "Wi-Fi 6", "app": "Home", "lastTask": "No task dispatched", "updated": now(),
            "workerPid": None, "stateDir": str(RUNTIME / f"kevin-{index+1:02d}"),
            "events": [{"time": now(), "kind": "system", "text": "Virtual device waiting to spawn"}]}

phones = {p["id"]: p for p in [make_phone(i) for i in range(8)]}
workers = {}
lock = threading.Lock()

def public_state():
    with lock:
        return {"fleet": "Kevin", "phones": list(phones.values()), "presets": {k: {"label": v[0], "description": v[1]} for k, v in TASK_PRESETS.items()}}

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
    system = "You are Kevin, a local fleet operator. Plan exactly one safe task for exactly one virtual phone. Never invent a phone id or preset. Return JSON only with keys phone_id, preset, reason. Use a preset when possible. If the user asks for a task not represented by a preset, use preset custom and put the exact task in reason. Do not claim to have sent messages, accessed accounts, or changed real devices: this is a local simulator."
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

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_): pass
    def send_json(self, code, data):
        raw=json.dumps(data).encode(); self.send_response(code); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(raw))); self.send_header("Cache-Control","no-store"); self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        path=urlparse(self.path).path
        if path=="/api/state": return self.send_json(200, public_state())
        if path=="/api/ollama/status": return self.send_json(200, ollama_status())
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
        except (ValueError, KeyError, json.JSONDecodeError, URLError, HTTPError, TimeoutError, OSError) as exc: return self.send_json(400,{"ok":False,"error":str(exc)})
        self.send_json(404,{"error":"not found"})

if __name__=="__main__":
    parser=argparse.ArgumentParser(); parser.add_argument("--port",type=int,default=8787); args=parser.parse_args(); RUNTIME.mkdir(exist_ok=True)
    for phone_id in phones: spawn_worker(phone_id)
    print(f"Kevin Muse Phone Lab listening on http://0.0.0.0:{args.port} with {len(phones)} worker processes")
    try: ThreadingHTTPServer(("0.0.0.0",args.port),Handler).serve_forever()
    finally:
        for phone_id in list(workers): stop_worker(phone_id)
