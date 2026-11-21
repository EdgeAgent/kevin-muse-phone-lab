#!/usr/bin/env python3
import json, os, time, urllib.request
BASE=os.environ.get('PHONEOPS_TEST_BASE','http://127.0.0.1:8787')
def get(path):
    with urllib.request.urlopen(BASE+path, timeout=5) as r: return json.load(r)
def post(path, body):
    req=urllib.request.Request(BASE+path,data=json.dumps(body).encode(),headers={'Content-Type':'application/json'},method='POST')
    with urllib.request.urlopen(req, timeout=10) as r: return json.load(r)
s=get('/api/state'); assert s['fleet']=='PhoneOps'; assert len(s['phones'])==8; assert sum(bool(p['workerPid']) for p in s['phones'])==8; assert all(p.get('runtime') for p in s['phones'])
print('PASS: eight worker processes are online')
result=post('/api/phones/kevin-01/tasks', {'preset':'health-scan'}); assert result['ok']; print('PASS: dispatched health-scan to kevin-01')
time.sleep(2.4); p=next(p for p in get('/api/state')['phones'] if p['id']=='kevin-01'); assert p['status']=='ready'; assert 'completed' in p['events'][0]['text']; print('PASS: worker completed task and reported event')
parallel=post('/api/parallel/dispatch', {'preset':'health-scan'}); assert parallel['ok']; assert parallel['parallel']['dispatched']==8; print('PASS: dispatched one workflow to all eight workers in parallel')
time.sleep(2.4); final=get('/api/state'); assert all(p['status']=='ready' for p in final['phones']); print('PASS: all eight parallel workers completed')
fleet=post('/api/agent/fleet', {'instruction':'Run a fleet health scan across all eight phone lanes'}); assert fleet['ok']; assert fleet['fleet']['planned']==8; print('PASS: AI fleet director planned all eight lanes')
time.sleep(2.4); evidence=get('/api/state'); assert all(p.get('lastEvidence') for p in evidence['phones']); print('PASS: fleet lanes produced explicit simulator evidence')
ollama=get('/api/ollama/status'); print('INFO: Ollama connected:', ollama['connected'], 'model:', ollama['model'])
print('ALL CHECKS PASSED')
