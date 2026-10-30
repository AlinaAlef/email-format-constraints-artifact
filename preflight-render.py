"""Render the 104 emails of the 52 risky pairs in real clients via the Preflight screenshot API.
usage: python3 -I preflight-render.py <env file with PREFLIGHT_TOKEN> ; writes preflight-results.json and PNGs under <run>/<brief>/<combo>/preflight/."""
import sys, json, time, os, urllib.request, urllib.error
ENV = sys.argv[1]
TOKEN = next(l.split('=', 1)[1].strip() for l in open(ENV) if l.startswith('PREFLIGHT_TOKEN='))
API = 'https://api.preflight.qa'
APPS = {"outlook_classic_win": {"modes": ["light"]}, "chrome_desktop": {"modes": ["light"]}}
jobs = json.load(open('preflight-jobs.json'))
out_path = 'preflight-results.json'
results = json.load(open(out_path)) if os.path.exists(out_path) else {}
def req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(API + path, data=data, method=method, headers={'Authorization': 'Bearer ' + TOKEN, 'Content-Type': 'application/json', 'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(r, timeout=60) as resp: return resp.status, json.load(resp)
    except urllib.error.HTTPError as e:
        try: return e.code, json.load(e)
        except Exception: return e.code, {'error': str(e)}
def key(j): return f"{j['set']}/{j['brief']}/{j['format']}/{j['slug']}"
# 1. submit
for j in jobs:
    k = key(j)
    if k in results and results[k].get('uuid'): continue
    html = open(j['path'], encoding='utf-8', errors='ignore').read()
    body = {"subject": f"{j['brief']} {j['format']} {j['slug']}", "html": html, "apps": APPS}
    while True:
        st, d = req('POST', '/screenshots', body)
        if st == 429:
            wait = int((d.get('retry_after') or (d.get('meta') or {}).get('retry_after') or 46)); print('429, wait', wait, flush=True); time.sleep(wait + 1); continue
        break
    uuid = d.get('uuid') or (d.get('meta') or {}).get('uuid') or (d.get('data') or {}).get('uuid')
    results[k] = {'job': j, 'uuid': uuid, 'post_status': st, 'post': {kk: vv for kk, vv in d.items() if kk != 'data'}, 'data': d.get('data')}
    json.dump(results, open(out_path, 'w'), indent=1)
    print(f"{len([r for r in results.values() if r.get('uuid')])}/{len(jobs)} submitted {k} -> {st} {uuid}", flush=True)
    if not uuid: print('  no uuid:', json.dumps(d)[:300], flush=True)
    time.sleep(46)
# 2. poll + download
pending = [k for k, r in results.items() if r.get('uuid') and not r.get('done')]
rounds = 0
while pending and rounds < 120:
    rounds += 1
    for k in list(pending):
        r = results[k]; st, d = req('GET', f"/screenshots/{r['uuid']}")
        if st == 429: time.sleep(10); continue
        r['get'] = d; data = d.get('data') or {}
        shots = data.get('screenshots') or []
        urls = [(f"{sh.get('app')}-{sh.get('mode')}", sh.get('url')) for sh in shots if sh.get('url')]
        statuses = [sh.get('status') for sh in shots]
        complete = bool(shots) and all(st_ in ('complete', 'completed', 'failed', 'error') for st_ in statuses)
        if urls and (complete or rounds > 100):
            j = r['job']; d_out = os.path.join(os.path.dirname(j['path']), 'preflight'); os.makedirs(d_out, exist_ok=True); saved = []
            for path, u in urls:
                name = path.strip('/').replace('/', '_').replace('[', '').replace(']', '') or 'shot'
                fn = os.path.join(d_out, name + '.png')
                try: urllib.request.urlretrieve(u, fn); saved.append(fn)
                except Exception as e: print('download fail', k, e, flush=True)
            r['done'] = True; r['saved'] = saved; pending.remove(k); print(f"done {k}: {len(saved)} images; statuses {sorted(set(statuses))}", flush=True)
        json.dump(results, open(out_path, 'w'), indent=1)
        time.sleep(5.5)
    if pending: print('pending', len(pending), 'round', rounds, flush=True); time.sleep(30)
print('FINISHED; pending', len(pending), flush=True)
