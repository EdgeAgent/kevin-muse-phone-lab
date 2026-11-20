#!/usr/bin/env python3
import concurrent.futures, json, os, time, urllib.request
from pathlib import Path

BASE = os.environ.get('PHONEOPS_URL', 'http://127.0.0.1:8787')
SITES = [
    'https://example.com', 'https://www.python.org/', 'https://www.wikipedia.org/',
    'https://github.com/', 'https://docs.python.org/3/', 'https://developer.mozilla.org/',
    'https://pypi.org/', 'https://www.ietf.org/',
]
CLK = os.sysconf(os.sysconf_names['SC_CLK_TCK'])
CPUS = os.cpu_count() or 1

def proc_snapshot():
    rows = {}
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit(): continue
        try:
            cmd = Path(entry / 'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='ignore')
            if not cmd: continue
            stat = (entry / 'stat').read_text().split()
            ppid = int(stat[3])
            rss_kb = int((entry / 'status').read_text().split('VmRSS:')[1].split()[0])
            cpu_ticks = int(stat[13]) + int(stat[14])
            rows[int(entry.name)] = {'ppid': ppid, 'cmd': cmd, 'rss_kb': rss_kb, 'cpu_ticks': cpu_ticks}
        except (FileNotFoundError, PermissionError, IndexError, ValueError):
            pass
    return rows

def farm_pids(rows):
    roots = {pid for pid, row in rows.items() if 'server.py --port 8787' in row['cmd'] or ('--headless' in row['cmd'] and '--remote-debugging-pipe' in row['cmd'])}
    selected = set(roots)
    changed = True
    while changed:
        changed = False
        for pid, row in rows.items():
            if row['ppid'] in selected and pid not in selected:
                selected.add(pid); changed = True
    return selected

def browser_pids(rows):
    roots = {pid for pid, row in rows.items() if 'playwright/driver/node' in row['cmd'] or ('--headless' in row['cmd'] and '--remote-debugging-pipe' in row['cmd'])}
    selected = set(roots)
    changed = True
    while changed:
        changed = False
        for pid, row in rows.items():
            if row['ppid'] in selected and pid not in selected:
                selected.add(pid); changed = True
    return selected

def farm_metrics():
    rows = proc_snapshot()
    selected = [rows[pid] for pid in farm_pids(rows)]
    browser = [rows[pid] for pid in browser_pids(rows)]
    return {
        'processes': len(selected),
        'rss_mb': round(sum(r['rss_kb'] for r in selected) / 1024, 1),
        'cpu_ticks': sum(r['cpu_ticks'] for r in selected),
        'browser_processes': len(browser),
        'browser_rss_mb': round(sum(r['rss_kb'] for r in browser) / 1024, 1),
        'browser_cpu_ticks': sum(r['cpu_ticks'] for r in browser),
    }

def navigate(item):
    phone, url = item
    started = time.perf_counter()
    body = json.dumps({'url': url}).encode()
    req = urllib.request.Request(f'{BASE}/api/phones/{phone}/browser/navigate', data=body, headers={'Content-Type':'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=60) as response:
        data = json.load(response)
    return {'phone': phone, 'url': url, 'elapsed_ms': round((time.perf_counter()-started)*1000, 1), 'ok': data.get('ok', False), 'title': data.get('browser', {}).get('title', '')}

def main():
    before = farm_metrics()
    samples = []
    stop = False
    def sampler():
        while not stop:
            samples.append({'t': time.time(), **farm_metrics()})
            time.sleep(0.1)
    import threading
    thread = threading.Thread(target=sampler, daemon=True); thread.start()
    started = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(navigate, [(f'kevin-{i:02d}', url) for i, url in enumerate(SITES, 1)]))
    elapsed_ms = (time.perf_counter()-started)*1000
    stop = True; thread.join(timeout=1)
    after = farm_metrics()
    peak = max(samples, key=lambda x: x['rss_mb']) if samples else after
    result = {
        'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'lanes': 8, 'sites': SITES,
        'elapsed_ms': round(elapsed_ms, 1), 'before': before, 'after': after,
        'peak': peak, 'min_lane_ms': min(r['elapsed_ms'] for r in results),
        'max_lane_ms': max(r['elapsed_ms'] for r in results),
        'avg_lane_ms': round(sum(r['elapsed_ms'] for r in results)/len(results), 1),
        'results': results,
    }
    Path('browser-benchmark.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))

if __name__ == '__main__': main()
