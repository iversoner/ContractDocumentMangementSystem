import urllib.request
import json

def api(method, path, data=None, token=None):
    url = f'http://localhost:5000{path}'
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    body = json.dumps(data).encode('utf-8') if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return json.loads(e.read())

# Login
result = api('POST', '/api/auth/login', {'username': 'admin', 'password': 'admin!'})
token = result['data']['token']
print('Login OK')

# Create a contract
result = api('POST', '/api/contracts', {
    'name': 'Test Contract',
    'category': '租赁',
    'company': 'Test Co',
    'agent': 'Zhang San',
    'startDate': '2026-06-01',
    'endDate': '2027-06-01'
}, token=token)
print(f"Create: {result.get('message')}")

# List contracts
result = api('GET', '/api/contracts', token=token)
items = result['data']['items']
print(f"List: total={result['data']['total']}, items={len(items)}")
for item in items:
    print(f"  [{item['id']}] {item['name']} | {item['company']} | {item['status']}")

# Delete all test contracts
for item in items:
    api('DELETE', f"/api/contracts/{item['id']}", token=token)
    print(f"Deleted: {item['name']}")
