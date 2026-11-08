#!/usr/bin/env python3
import json, time, urllib.request
BASE='http://127.0.0.1:8787'
def get(path):
    with urllib.request.urlopen(BASE+path, timeout=5) as r: return json.load(r)
def post(path, body):
    req=urllib.request.Request(BASE+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(req, timeout=10) as r: return json.load(r)
s=get('/api/state'); assert s['fleet']=='Kevin'; assert len(s['phones'])==8; assert sum(bool(p['workerPid']) for p in s['phones'])==8
print('PASS: eight worker processes are online')
result=post('/api/phones/kevin-01/tasks', {'preset':'health-scan'}); assert result['ok']; print('PASS: dispatched health-scan to kevin-01')
time.sleep(2.4); p=next(p for p in get('/api/state')['phones'] if p['id']=='kevin-01'); assert p['status']=='ready'; assert 'completed' in p['events'][0]['text']; print('PASS: worker completed task and reported event')
ollama=get('/api/ollama/status'); print('INFO: Ollama connected:', ollama['connected'], 'model:', ollama['model'])
print('ALL CHECKS PASSED')
