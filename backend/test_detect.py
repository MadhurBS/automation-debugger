import requests, json, io, zipfile

r = requests.post('http://127.0.0.1:8000/api/v1/auth/login',
    json={'email': 'admin@automation-debugger.com', 'password': 'Admin1234'})
token = r.json()['access_token']
hdrs = {'Authorization': 'Bearer ' + token}

def test(label, fname, data, expected):
    resp = requests.post(
        'http://127.0.0.1:8000/api/v1/projects/detect-platform',
        headers=hdrs,
        files={'file': (fname, io.BytesIO(data), 'application/octet-stream')}
    )
    body = resp.json()
    got  = body.get('platform', '?')
    conf = body.get('confidence', 0)
    mark = 'PASS' if got == expected else 'FAIL'
    print(f'{label:<35} expected={expected:<22} got={got:<22} conf={conf:.0%}  {mark}')

# UiPath ZIP
buf = io.BytesIO()
with zipfile.ZipFile(buf, 'w') as zf:
    zf.writestr('project.json', json.dumps({'studioVersion': '21.10', 'projectVersion': '1.0', 'name': 'Bot'}))
test('UiPath ZIP', 'bot.zip', buf.getvalue(), 'uipath')

# Blue Prism ZIP
buf2 = io.BytesIO()
with zipfile.ZipFile(buf2, 'w') as zf:
    bp_xml = '<process name="BP"><stage type="Start" /></process>'
    zf.writestr('MyProcess.bprelease', bp_xml)
test('Blue Prism ZIP', 'bp.zip', buf2.getvalue(), 'blue_prism')

# Automation Anywhere ZIP
buf3 = io.BytesIO()
with zipfile.ZipFile(buf3, 'w') as zf:
    aa = json.dumps({'commandList': [{'command': 'SetText', 'name': 'Step1'}], 'name': 'MyBot'})
    zf.writestr('bot.json', aa)
test('Automation Anywhere ZIP', 'aa.zip', buf3.getvalue(), 'automation_anywhere')

# Plain UiPath project.json
buf4 = io.BytesIO(json.dumps({'studioVersion': '21.10', 'projectVersion': '1.0'}).encode())
test('UiPath project.json direct', 'project.json', buf4.getvalue(), 'uipath')

print('Done.')
