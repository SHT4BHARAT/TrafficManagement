import urllib.request, json

BASE = 'http://localhost:8000'

def post(path, body=None):
    data = json.dumps(body).encode() if body is not None else b''
    req = urllib.request.Request(BASE+path, data=data, headers={'Content-Type':'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=3) as r:
            return r.status, json.loads(r.read())
    except Exception as e:
        return 0, str(e)

tests = [
    ('MANUAL mode',   '/api/controller-config', {'mode':'manual'}),
    ('AUTO mode',     '/api/controller-config', {'mode':'auto'}),
    ('RR mode',       '/api/controller-config', {'mode':'rr'}),
    ('APPLY VPM',     '/api/controller-config', {'mode':'manual','vps':{'N':14,'S':11,'E':6,'W':22}}),
    ('TRIGGER EMERG', '/api/emergency/request', {'zone':'INT_001','start':'INT_001','end':'INT_020','device_id':'DASHBOARD'}),
    ('CLEAR EMERG',   '/api/emergency/clear',   None),
    ('PHASE NS',      '/api/select-phase',      {'phase':'NS'}),
    ('PHASE EW',      '/api/select-phase',      {'phase':'EW'}),
]

print('BUTTON TEST RESULTS')
print('='*60)
all_pass = True
for name, path, body in tests:
    status, resp = post(path, body)
    is_err = isinstance(resp, dict) and resp.get('status') == 'error'
    tag = 'PASS' if status == 200 and not is_err else 'FAIL'
    if tag == 'FAIL':
        all_pass = False
    print(f"[{tag}] {name}: {resp}")

print('='*60)
print('ALL PASS' if all_pass else 'SOME FAILURES DETECTED')
