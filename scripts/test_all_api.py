"""Comprehensive CRUD test for all modules"""
import urllib.request, urllib.error, json, os, io

BASE = 'http://localhost:5000'
TOKEN = None

def api(method, path, data=None, raw=False):
    url = f'{BASE}{path}'
    headers = {}
    if TOKEN:
        headers['Authorization'] = f'Bearer {TOKEN}'
    if isinstance(data, dict):
        body = json.dumps(data).encode('utf-8')
        headers['Content-Type'] = 'application/json'
    elif isinstance(data, bytes):
        body = data
    else:
        body = None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read()) if not raw else resp.read()
    except urllib.error.HTTPError as e:
        return json.loads(e.read())

def ok(r):
    return r.get('success', False)

# ============================================================
# 1. Auth
# ============================================================
print('='*60)
print('1. AUTH')
r = api('POST', '/api/auth/login', {'username': 'admin', 'password': 'admin!'})
TOKEN = r['data']['token']
print(f'  Login: {ok(r)} - {r.get("message")}')

r = api('GET', '/api/auth/me')
print(f'  Me: {ok(r)} - {r.get("data",{}).get("username")}')

# ============================================================
# 2. Contract
# ============================================================
print('='*60)
print('2. CONTRACT')
r = api('POST', '/api/contracts', {
    'name': '办公租赁合同', 'category': '租赁', 'company': '测试公司A',
    'agent': '张三', 'startDate': '2026-06-01', 'endDate': '2027-06-01',
    'contactPerson': '李四', 'contactPhone': '13800138000', 'remark': '测试新增'
})
cid = r.get('data',{}).get('id')
print(f'  Create: {ok(r)} - id={cid} - {r.get("message")}')

r = api('GET', '/api/contracts')
print(f'  List: {ok(r)} - total={r.get("data",{}).get("total")}')

r = api('PUT', f'/api/contracts/{cid}', {
    'name': '办公租赁合同(已修改)', 'category': '租赁', 'company': '测试公司A',
    'agent': '张三', 'startDate': '2026-06-01', 'endDate': '2027-12-31',
})
print(f'  Update: {ok(r)} - {r.get("message")}')

# ============================================================
# 3. Patent
# ============================================================
print('='*60)
print('3. PATENT')
r = api('POST', '/api/patents', {
    'name': 'AI算法专利', 'patentNo': 'CN20260001', 'type': '发明专利',
    'holder': '测试公司A', 'agent': '王五',
    'applicationDate': '2026-06-01', 'expireDate': '2036-06-01',
    'remark': '测试新增专利'
})
pid = r.get('data',{}).get('id')
print(f'  Create: {ok(r)} - id={pid} - {r.get("message")}')

r = api('GET', '/api/patents')
print(f'  List: {ok(r)} - total={r.get("data",{}).get("total")}')

r = api('PUT', f'/api/patents/{pid}', {
    'name': 'AI算法专利(修改)', 'patentNo': 'CN20260001', 'type': '发明专利',
    'holder': '测试公司A', 'agent': '王五',
    'applicationDate': '2026-06-01', 'expireDate': '2036-06-01',
})
print(f'  Update: {ok(r)} - {r.get("message")}')

# ============================================================
# 4. Insurance
# ============================================================
print('='*60)
print('4. INSURANCE')
r = api('POST', '/api/insurances', {
    'plateNo': '京A12345', 'brand': '宝马X5', 'insuranceCompany': '平安保险',
    'insuranceType': '商业险', 'amount': 8000, 'agent': '赵六',
    'startDate': '2026-06-01', 'endDate': '2027-06-01',
    'remark': '测试新增车险'
})
iid = r.get('data',{}).get('id')
print(f'  Create: {ok(r)} - id={iid} - {r.get("message")}')

r = api('GET', '/api/insurances')
print(f'  List: {ok(r)} - total={r.get("data",{}).get("total")}')

r = api('PUT', f'/api/insurances/{iid}', {
    'plateNo': '京A12345', 'brand': '宝马X5', 'insuranceCompany': '平安保险',
    'insuranceType': '商业险', 'amount': 9000, 'agent': '赵六',
    'startDate': '2026-06-01', 'endDate': '2027-06-01',
})
print(f'  Update: {ok(r)} - {r.get("message")}')

# ============================================================
# 5. File upload
# ============================================================
print('='*60)
print('5. FILE')
# Create a test file
test_content = b'Hello, this is a test file for Suzhen system.'
# Use multipart upload
boundary = '----TestBoundary12345'
body = b''
body += f'--{boundary}\r\n'.encode()
body += b'Content-Disposition: form-data; name="category"\r\n\r\n'
body += b'\xe5\x90\x88\xe5\x90\x8c\r\n'  # 合同 in utf-8
body += f'--{boundary}\r\n'.encode()
body += b'Content-Disposition: form-data; name="file"; filename="test.txt"\r\n'
body += b'Content-Type: text/plain\r\n\r\n'
body += test_content + b'\r\n'
body += f'--{boundary}--\r\n'.encode()

headers = {'Content-Type': f'multipart/form-data; boundary={boundary}'}
req = urllib.request.Request(f'{BASE}/api/files/upload', data=body, headers=headers, method='POST')
req.add_header('Authorization', f'Bearer {TOKEN}')
try:
    resp = urllib.request.urlopen(req)
    r = json.loads(resp.read())
    fid = r.get('data',{}).get('id')
    print(f'  Upload: {ok(r)} - id={fid} - {r.get("message")}')
except urllib.error.HTTPError as e:
    r = json.loads(e.read())
    print(f'  Upload: False - {r.get("message")}')

r = api('GET', '/api/files')
print(f'  List: {ok(r)} - total={r.get("data",{}).get("total")}')

# ============================================================
# 6. User
# ============================================================
print('='*60)
print('6. USER')
r = api('POST', '/api/users', {
    'username': 'testuser', 'password': 'test123!', 'displayName': '测试用户',
    'email': 'test@test.com', 'role': '业务员'
})
uid = r.get('data',{}).get('id')
print(f'  Create: {ok(r)} - id={uid} - {r.get("message")}')

r = api('GET', '/api/users')
print(f'  List: {ok(r)} - total={r.get("data",{}).get("total")}')

r = api('PUT', f'/api/users/{uid}', {
    'username': 'testuser', 'displayName': '测试用户(已修改)',
    'email': 'test2@test.com', 'role': '业务员'
})
print(f'  Update: {ok(r)} - {r.get("message")}')

# ============================================================
# 7. Logs
# ============================================================
print('='*60)
print('7. LOGS')
r = api('GET', '/api/logs')
print(f'  List: {ok(r)} - total={r.get("data",{}).get("total")}')

# ============================================================
# 8. Dashboard
# ============================================================
print('='*60)
print('8. DASHBOARD')
r = api('GET', '/api/dashboard/stats')
print(f'  Stats: {ok(r)} - {json.dumps(r.get("data"), ensure_ascii=False)}')

r = api('GET', '/api/dashboard/recent')
print(f'  Recent: {ok(r)} - items={len(r.get("data", []))}')

r = api('GET', '/api/dashboard/expiring')
print(f'  Expiring: {ok(r)} - items={len(r.get("data", []))}')

# ============================================================
# 9. Settings
# ============================================================
print('='*60)
print('9. SETTINGS')
r = api('GET', '/api/settings')
print(f'  Get: {ok(r)}')

# ============================================================
# 10. Export
# ============================================================
print('='*60)
print('10. EXPORT')
r = api('POST', '/api/export', {'type': 'all', 'format': 'json'})
print(f'  Export all JSON: {ok(r)} - keys={list(r.get("data",{}).keys()) if r.get("data") else "N/A"}')

print('='*60)
print('ALL TESTS COMPLETE')
