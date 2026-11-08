#!/usr/bin/env python3
"""One lightweight virtual phone: isolated cwd/state dir, stdin task queue, stdout events."""
import argparse, json, os, sys, time
parser=argparse.ArgumentParser(); parser.add_argument('--phone-id',required=True); parser.add_argument('--name',required=True); parser.add_argument('--state-dir',required=True); args=parser.parse_args()
os.makedirs(args.state_dir,exist_ok=True)
state_file=os.path.join(args.state_dir,'phone-state.json')
state={'phoneId':args.phone_id,'name':args.name,'bootedAt':time.time(),'cwd':os.getcwd(),'files':[]}
with open(state_file,'w') as f: json.dump(state,f,indent=2)
for line in sys.stdin:
    try: task=json.loads(line)
    except json.JSONDecodeError: continue
    print(json.dumps({'type':'started',**task}),flush=True)
    time.sleep(float(task.get('delay',3)))
    app={'check-inbox':'Messages','capture-screen':'Gallery','health-scan':'Diagnostics','open-calendar':'Calendar','draft-reply':'Messages'}.get(task.get('key'),'Home')
    result_file=os.path.join(args.state_dir,'last-result.json')
    with open(result_file,'w') as f: json.dump({'taskId':task['taskId'],'command':task['command'],'completedAt':time.time()},f,indent=2)
    print(json.dumps({'type':'completed','app':app,**task}),flush=True)
