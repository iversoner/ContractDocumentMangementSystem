"""批量迁移 insurance/files/users/logs/settings/export — MockData→API"""
import os

PAGES = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'pages')

def patch(path, pairs):
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()
    for t in pairs:
        old, new = t[0], t[1]
        if old not in c:
            print(f"  WARN: old not found: {old[:60]}...")
        c = c.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)
    print(f"  OK {os.path.basename(path)}")


# ==== insurance.html ====
def migrate_insurance():
    path = os.path.join(PAGES, 'insurance.html')
    pairs = [
        # filterIns → loadInsurances
        ('''    function filterIns() {
      const status = document.getElementById('filterInsStatus').value;
      const company = document.getElementById('filterInsCompany').value;
      const kw = document.getElementById('insSearch').value.toLowerCase();
      return MockData.insurances.filter(i => {
        if (status && i.status !== status) return false;
        if (company && i.insuranceCompany !== company) return false;
        if (kw && !i.plateNo.toLowerCase().includes(kw) && !i.brand.toLowerCase().includes(kw)) return false;
        return true;
      });
    }''',
         '''    async function loadInsurances() {
      const params = { page: insPage, pageSize: insPageSize };
      if (document.getElementById('filterInsStatus').value) params.status = document.getElementById('filterInsStatus').value;
      if (document.getElementById('filterInsCompany').value) params.company = document.getElementById('filterInsCompany').value;
      if (document.getElementById('insSearch').value) params.keyword = document.getElementById('insSearch').value;
      try { const res = await API.get('/insurances', params); return res.data; }
      catch (err) { showToast('加载失败: ' + err.message, 'error'); return { items: [], total: 0 }; }
    }'''),

        # renderInsTable 开头
        ('''    function renderInsTable() {
      const filtered = filterIns();
      const totalPages = Math.ceil(filtered.length / insPageSize);
      const start = (insPage - 1) * insPageSize;
      const pageData = filtered.slice(start, start + insPageSize);
      const tbody = document.getElementById('insTableBody');''',
         '''    async function renderInsTable() {
      const data = await loadInsurances();
      const tbody = document.getElementById('insTableBody');'''),

        ("pageData.length === 0", "data.items.length === 0"),
        ("pageData.map(i =>", "data.items.map(i =>"),
        ("filtered.length / insPageSize", "data.total / insPageSize"),

        # goInsPage
        ('''    function goInsPage(p) {
      const totalPages = Math.ceil(filterIns().length / insPageSize);
      if (p < 1 || p > totalPages) return;
      insPage = p;
      renderInsTable();
    }''',
         '''    function goInsPage(p) { insPage = p; renderInsTable(); }'''),

        # editIns
        ("    function editIns(id) {\n      const i = MockData.insurances.find(x => x.id === id); if (!i) return;",
         "    function editIns(id) {\n      API.get('/insurances/' + id).then(res => { const i = res.data;"),
        ("      document.getElementById('insFilePath').value = i.filePath;\n      document.getElementById('insRemark').value = i.remark;\n      openModal('insModal');\n    }",
         "      document.getElementById('insFilePath').value = i.filePath || '';\n      document.getElementById('insRemark').value = i.remark || '';\n      openModal('insModal');\n    }).catch(err => showToast('获取车险失败: ' + err.message, 'error'));\n    }"),
        ("i.createTime.substring(0, 10)", "(i.createdAt || i.createTime || '').substring(0, 10)"),
        ("i.expireTime", "i.endDate || i.expireTime"),

        # saveIns
        ('''    function saveIns(e) {
      e.preventDefault();
      const id = document.getElementById('insId').value;
      const now = new Date().toISOString().replace('T', ' ').substring(0, 19);
      const expDate = document.getElementById('insExpireDate').value;
      const today = new Date().toISOString().substring(0, 10);
      let status = 'active';
      if (expDate < today) status = 'expired';
      else if (expDate <= new Date(Date.now() + 30 * 86400000).toISOString().substring(0, 10)) status = 'expiring';

      const data = {
        id: id ? parseInt(id) : Math.max(...MockData.insurances.map(x => x.id), 0) + 1,
        plateNo: document.getElementById('insPlateNo').value,
        brand: document.getElementById('insBrand').value,
        insuranceCompany: document.getElementById('insCompany').value,
        insuranceType: document.getElementById('insType').value,
        amount: parseFloat(document.getElementById('insAmount').value) || 0,
        agent: document.getElementById('insAgent').value,
        createTime: id ? MockData.insurances.find(x => x.id === parseInt(id)).createTime : now,
        expireTime: expDate,
        status: status,
        filePath: document.getElementById('insFilePath').value || `/files/insurance_new.pdf`,
        remark: document.getElementById('insRemark').value,
      };

      if (id) {
        MockData.insurances[MockData.insurances.findIndex(x => x.id === parseInt(id))] = data;
        showToast('车险记录已更新', 'success');
      } else {
        MockData.insurances.unshift(data);
        showToast('车险记录已添加', 'success');
      }
      closeModal('insModal');
      renderInsTable();
    }''',
         '''    async function saveIns(e) {
      e.preventDefault();
      const id = document.getElementById('insId').value;
      const body = {
        plateNo: document.getElementById('insPlateNo').value,
        brand: document.getElementById('insBrand').value,
        insuranceCompany: document.getElementById('insCompany').value,
        insuranceType: document.getElementById('insType').value,
        amount: parseFloat(document.getElementById('insAmount').value) || 0,
        agent: document.getElementById('insAgent').value,
        startDate: document.getElementById('insCreateDate').value,
        endDate: document.getElementById('insExpireDate').value,
        filePath: document.getElementById('insFilePath').value,
        remark: document.getElementById('insRemark').value,
      };
      try {
        if (id) { await API.put('/insurances/' + id, body); showToast('车险记录已更新', 'success'); }
        else { await API.post('/insurances', body); showToast('车险记录已添加', 'success'); }
        closeModal('insModal'); renderInsTable();
      } catch (err) { showToast('保存失败: ' + err.message, 'error'); }
    }'''),

        # viewIns
        ("    function viewIns(id) {\n      const i = MockData.insurances.find(x => x.id === id); if (!i) return;",
         "    async function viewIns(id) {\n      try { const res = await API.get('/insurances/' + id); const i = res.data;"),
        ("${i.createTime}", "${i.createdAt || i.createTime}"),
        ("${i.expireTime}", "${i.endDate || i.expireTime}"),
        ("${i.filePath}", "${i.filePath || '无'}"),
        ("      openModal('insDetailModal');\n    }",
         "      openModal('insDetailModal');\n      } catch (err) { showToast('加载失败: ' + err.message, 'error'); }\n    }"),

        # 统计 (MockData.insurances → API)
        ("MockData.insurances.length", "data.items.length"),
        ('''MockData.insurances.filter(i => i.status === 'active').length''',
         '''data.items.filter(i => i.status === 'active').length'''),
        ('''MockData.insurances.filter(i => i.status === 'expiring').length''',
         '''data.items.filter(i => i.status === 'expiring').length'''),
        ('''MockData.insurances.filter(i => i.status === 'expired').length''',
         '''data.items.filter(i => i.status === 'expired').length'''),

        # 删除按钮
        ("onclick=\"confirmAction('确定删除车险记录「${i.plateNo}」吗？', () => { MockData.insurances = MockData.insurances.filter(x => x.id !== ${i.id}); renderInsTable(); })\"",
         "onclick=\"deleteIns(${i.id}, '${i.plateNo.replace(/'/g, \"\\\\'\")}')\""),
    ]
    patch(path, pairs)
    # 添加 deleteIns 和 updateStats
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()
    add = '''\n    async function deleteIns(id, plate) {\n      if (!confirm('确定删除车险记录「' + plate + '」吗？')) return;\n      try { await API.del('/insurances/' + id); showToast('车险记录已删除', 'success'); renderInsTable(); }\n      catch (err) { showToast('删除失败: ' + err.message, 'error'); }\n    }'''
    if 'function deleteIns' not in c:
        c = c.replace('function goInsPage(p)', 'function goInsPage(p)' + add)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)


# ==== files.html ====
def migrate_files():
    path = os.path.join(PAGES, 'files.html')
    pairs = [
        ('''    function filterFiles() {
      const category = document.getElementById('filterFileCategory').value;
      const kw = document.getElementById('fileSearch').value.toLowerCase();
      return MockData.files.filter(f => {
        if (category && f.category !== category) return false;
        if (kw && !f.name.toLowerCase().includes(kw)) return false;
        return true;
      });
    }''',
         '''    async function loadFiles() {
      const params = { page: filePage, pageSize: filePageSize };
      if (document.getElementById('filterFileCategory').value) params.category = document.getElementById('filterFileCategory').value;
      if (document.getElementById('fileSearch').value) params.keyword = document.getElementById('fileSearch').value;
      try { const res = await API.get('/files', params); return res.data; }
      catch (err) { showToast('加载失败: ' + err.message, 'error'); return { items: [], total: 0 }; }
    }'''),

        ('''    function renderFileTable() {
      const filtered = filterFiles();
      const totalPages = Math.ceil(filtered.length / filePageSize);
      const start = (filePage - 1) * filePageSize;
      const pageData = filtered.slice(start, start + filePageSize);
      const tbody = document.getElementById('fileTableBody');''',
         '''    async function renderFileTable() {
      const data = await loadFiles();
      const tbody = document.getElementById('fileTableBody');'''),

        ("pageData.length === 0", "data.items.length === 0"),
        ("pageData.map(f =>", "data.items.map(f =>"),
        ("filtered.length / filePageSize", "data.total / filePageSize"),

        # 字段适配: size (int) → format, uploadTime → createdAt, uploader → uploader, storedPath → storedPath
        ("${f.size}", "${formatFileSize(f.size)}"),
        ("${f.uploadTime}", "${f.createdAt || f.uploadTime}"),
        ("${f.path}", "${f.storedPath || f.path}"),

        ('''    function goFilePage(p) {
      const totalPages = Math.ceil(filterFiles().length / filePageSize);
      if (p < 1 || p > totalPages) return;
      filePage = p;
      renderFileTable();
    }''',
         '''    function goFilePage(p) { filePage = p; renderFileTable(); }'''),

        # 删除按钮
        ("onclick=\"confirmAction('确定删除文件「${f.name}」吗？', () => { MockData.files = MockData.files.filter(x => x.id !== ${f.id}); renderFileTable(); })\"",
         "onclick=\"deleteFile(${f.id}, '${f.name.replace(/'/g, \"\\\\'\")}')\""),

        # 上传按钮
        ("showToast('文件已准备上传 (模拟)', 'info')",
         "document.getElementById('fileUploadInput').click()"),
        ("showToast('已开始下载 (模拟)', 'info')",
         "downloadSelected()"),
    ]
    patch(path, pairs)
    # 添加 deleteFile 和 upload 函数, 以及隐藏的 file input
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()

    add_fn = '''\n    async function deleteFile(id, name) {\n      if (!confirm('确定删除文件「' + name + '」吗？')) return;\n      try { await API.del('/files/' + id); showToast('文件已删除', 'success'); renderFileTable(); }\n      catch (err) { showToast('删除失败: ' + err.message, 'error'); }\n    }\n    function downloadSelected() {\n      const selected = prompt('请输入要下载的文件ID:');\n      if (selected) { API.download('/files/' + selected + '/download', ''); }\n    }'''
    if 'function deleteFile' not in c:
        c = c.replace('function goFilePage(p)', 'function goFilePage(p)' + add_fn)

    # 插入隐藏的 file input 和上传逻辑
    upload_html = '''
      <input type="file" id="fileUploadInput" style="display:none;" onchange="handleFileUpload(this)" multiple>
      <select id="uploadCategory" style="display:none;">
        <option value="合同">合同</option>
        <option value="专利">专利</option>
        <option value="车险续期">车险续期</option>
      </select>'''
    if 'fileUploadInput' not in c:
        c = c.replace('</main>', upload_html + '\n</main>')

    upload_script = '''\n    async function handleFileUpload(input) {\n      if (!input.files.length) return;\n      const cat = prompt('选择文件类别: 合同/专利/车险续期', '合同');\n      if (!['合同','专利','车险续期'].includes(cat)) { showToast('无效类别', 'error'); return; }\n      for (const file of input.files) {\n        const fd = new FormData();\n        fd.append('file', file);\n        fd.append('category', cat);\n        try {\n          await API.upload('/files/upload', fd);\n          showToast(file.name + ' 上传成功', 'success');\n        } catch (err) { showToast(file.name + ' 上传失败: ' + err.message, 'error'); }\n      }\n      renderFileTable();\n      input.value = '';\n    }'''
    if 'handleFileUpload' not in c:
        c = c.replace('document.addEventListener', upload_script + '\n\n    document.addEventListener')

    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)


# ==== users.html ====
def migrate_users():
    path = os.path.join(PAGES, 'users.html')
    pairs = [
        ('''    function filterUsers() {
      const role = document.getElementById('filterUserRole').value;
      const status = document.getElementById('filterUserStatus').value;
      const kw = document.getElementById('userSearch').value.toLowerCase();
      return MockData.users.filter(u => {
        if (role && u.role !== role) return false;
        if (status && u.status !== status) return false;
        if (kw && !u.username.toLowerCase().includes(kw) && !u.displayName.toLowerCase().includes(kw)) return false;
        return true;
      });
    }''',
         '''    async function loadUsers() {
      const params = { page: userPage, pageSize: userPageSize };
      if (document.getElementById('filterUserRole').value) params.role = document.getElementById('filterUserRole').value;
      if (document.getElementById('filterUserStatus').value) params.status = document.getElementById('filterUserStatus').value;
      if (document.getElementById('userSearch').value) params.keyword = document.getElementById('userSearch').value;
      try { const res = await API.get('/users', params); return res.data; }
      catch (err) { showToast('加载失败: ' + err.message, 'error'); return { items: [], total: 0 }; }
    }'''),

        ('''    function renderUserTable() {
      const filtered = filterUsers();
      const totalPages = Math.ceil(filtered.length / userPageSize);
      const start = (userPage - 1) * userPageSize;
      const pageData = filtered.slice(start, start + userPageSize);
      const tbody = document.getElementById('userTableBody');''',
         '''    async function renderUserTable() {
      const data = await loadUsers();
      const tbody = document.getElementById('userTableBody');'''),

        ("pageData.length === 0", "data.items.length === 0"),
        ("pageData.map(u =>", "data.items.map(u =>"),
        ("filtered.length / userPageSize", "data.total / userPageSize"),
        ("${u.createTime}", "${u.createdAt || u.createTime}"),

        # 状态显示
        ("${u.status}", "${u.status}"),

        ('''    function goUserPage(p) {
      const totalPages = Math.ceil(filterUsers().length / userPageSize);
      if (p < 1 || p > totalPages) return;
      userPage = p;
      renderUserTable();
    }''',
         '''    function goUserPage(p) { userPage = p; renderUserTable(); }'''),

        # editUser
        ("    function editUser(id) {\n      const u = MockData.users.find(x => x.id === id); if (!u) return;",
         "    function editUser(id) {\n      API.get('/users/' + id).then(res => { const u = res.data;"),
        ("document.getElementById('userPassword').required = false;\n      openModal('userModal');\n    }",
         "document.getElementById('userPassword').required = false;\n      openModal('userModal');\n    }).catch(err => showToast('获取用户失败: ' + err.message, 'error'));\n    }"),

        # saveUser
        ('''    function saveUser(e) {
      e.preventDefault();
      const id = document.getElementById('userId').value;
      const now = new Date().toISOString().replace('T', ' ').substring(0, 19);
      const data = {
        id: id ? parseInt(id) : Math.max(...MockData.users.map(x => x.id), 0) + 1,
        username: document.getElementById('userUsername').value,
        displayName: document.getElementById('userDisplayName').value,
        email: document.getElementById('userEmail').value,
        role: document.getElementById('userRole').value,
        status: 'active',
        createTime: id ? MockData.users.find(x => x.id === parseInt(id)).createTime : now,
      };

      if (id) {
        MockData.users[MockData.users.findIndex(x => x.id === parseInt(id))] = data;
        showToast('用户已更新', 'success');
      } else {
        MockData.users.unshift(data);
        showToast('用户已添加，初始密码已设置', 'success');
      }
      closeModal('userModal');
      renderUserTable();
    }''',
         '''    async function saveUser(e) {
      e.preventDefault();
      const id = document.getElementById('userId').value;
      const body = {
        username: document.getElementById('userUsername').value,
        displayName: document.getElementById('userDisplayName').value,
        email: document.getElementById('userEmail').value,
        role: document.getElementById('userRole').value,
      };
      if (!id) body.password = document.getElementById('userPassword').value;
      try {
        if (id) { await API.put('/users/' + id, body); showToast('用户已更新', 'success'); }
        else { await API.post('/users', body); showToast('用户已添加', 'success'); }
        closeModal('userModal'); renderUserTable();
      } catch (err) { showToast('保存失败: ' + err.message, 'error'); }
    }'''),

        # 重置密码
        ("showToast('用户「${u.displayName}」密码已重置 (模拟)', 'info')",
         "resetUserPassword(${u.id}, '${u.displayName.replace(/'/g, \"\\\\'\")}')"),

        # 删除按钮
        ("onclick=\"confirmAction('确定删除用户「${u.displayName}」吗？', () => { MockData.users = MockData.users.filter(x => x.id !== ${u.id}); renderUserTable(); })\"",
         "onclick=\"deleteUser(${u.id}, '${u.displayName.replace(/'/g, \"\\\\'\")}')\""),
    ]
    patch(path, pairs)
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()
    add = '''\n    async function deleteUser(id, name) {\n      if (!confirm('确定删除用户「' + name + '」吗？')) return;\n      try { await API.del('/users/' + id); showToast('用户已删除', 'success'); renderUserTable(); }\n      catch (err) { showToast('删除失败: ' + err.message, 'error'); }\n    }\n    async function resetUserPassword(id, name) {\n      const newPwd = prompt('输入用户「' + name + '」的新密码:', '123456');\n      if (!newPwd) return;\n      try { const res = await API.put('/users/' + id + '/reset-password', { password: newPwd }); showToast(res.message, 'success'); }\n      catch (err) { showToast('重置失败: ' + err.message, 'error'); }\n    }'''
    if 'function deleteUser' not in c:
        c = c.replace('function goUserPage(p)', 'function goUserPage(p)' + add)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)


# ==== logs.html ====
def migrate_logs():
    path = os.path.join(PAGES, 'logs.html')
    pairs = [
        ('''    function filterLogs() {
      const level = document.getElementById('filterLogLevel').value;
      const module = document.getElementById('filterLogModule').value;
      const kw = document.getElementById('logSearch').value.toLowerCase();
      return MockData.logs.filter(l => {
        if (level && l.level !== level) return false;
        if (module && l.module !== module) return false;
        if (kw && !l.action.toLowerCase().includes(kw) && !l.detail.toLowerCase().includes(kw) && !l.user.toLowerCase().includes(kw)) return false;
        return true;
      });
    }''',
         '''    async function loadLogs() {
      const params = { page: logPage, pageSize: logPageSize };
      if (document.getElementById('filterLogLevel').value) params.level = document.getElementById('filterLogLevel').value;
      if (document.getElementById('filterLogModule').value) params.module = document.getElementById('filterLogModule').value;
      if (document.getElementById('logSearch').value) params.keyword = document.getElementById('logSearch').value;
      try { const res = await API.get('/logs', params); return res.data; }
      catch (err) { showToast('加载失败: ' + err.message, 'error'); return { items: [], total: 0 }; }
    }'''),

        ('''    function renderLogTable() {
      const filtered = filterLogs();
      const totalPages = Math.ceil(filtered.length / logPageSize);
      const start = (logPage - 1) * logPageSize;
      const pageData = filtered.slice(start, start + logPageSize);
      const tbody = document.getElementById('logTableBody');''',
         '''    async function renderLogTable() {
      const data = await loadLogs();
      const tbody = document.getElementById('logTableBody');'''),

        ("pageData.length === 0", "data.items.length === 0"),
        ("pageData.map(l =>", "data.items.map(l =>"),
        ("filtered.length / logPageSize", "data.total / logPageSize"),
        ("${l.time}", "${l.createdAt || l.time}"),
        ("${l.user}", "${l.username || l.user}"),

        ('''    function goLogPage(p) {
      const totalPages = Math.ceil(filterLogs().length / logPageSize);
      if (p < 1 || p > totalPages) return;
      logPage = p;
      renderLogTable();
    }''',
         '''    function goLogPage(p) { logPage = p; renderLogTable(); }'''),

        # 清空按钮
        ("showToast('日志已清空 (模拟)', 'warning')",
         "clearAllLogs()"),
    ]
    patch(path, pairs)
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()
    add = '''\n    async function clearAllLogs() {\n      if (!confirm('确定清空所有日志吗？此操作不可恢复！')) return;\n      try { await API.del('/logs'); showToast('日志已清空', 'success'); renderLogTable(); }\n      catch (err) { showToast('清空失败: ' + err.message, 'error'); }\n    }'''
    if 'function clearAllLogs' not in c:
        c = c.replace('function goLogPage(p)', 'function goLogPage(p)' + add)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)


# ==== settings.html ====
def migrate_settings():
    path = os.path.join(PAGES, 'settings.html')
    pairs = [
        # saveSettings
        ('''    function saveSettings() {
      showToast('所有配置已保存 (模拟，后端未实现)', 'success');
    }''',
         '''    async function saveSettings() {
      const body = {
        email: {
          smtpServer: document.getElementById('smtpServer').value,
          smtpPort: parseInt(document.getElementById('smtpPort').value) || 587,
          username: document.getElementById('smtpUser').value,
          password: document.getElementById('smtpPass').value,
          useTLS: document.getElementById('useTLS').checked,
          senderName: document.getElementById('senderName').value,
        },
        database: {
          path: document.getElementById('dbPath').value,
          backupEnabled: document.getElementById('backupEnabled').checked,
          backupInterval: document.getElementById('backupInterval').value,
        },
        storage: {
          uploadFolder: document.getElementById('uploadFolder').value,
          maxFileSize: parseInt(document.getElementById('maxFileSize').value) * 1024 * 1024 || 10485760,
          allowedTypes: document.getElementById('allowedTypes').value,
        },
        reminder: {
          enabled: document.getElementById('remindEnabled').checked,
          daysBefore: parseInt(document.getElementById('daysBefore').value) || 30,
          sendTime: document.getElementById('sendTime').value,
          recipients: document.getElementById('remindRecipients').value,
        },
      };
      try { await API.put('/settings', body); showToast('配置已保存', 'success'); }
      catch (err) { showToast('保存失败: ' + err.message, 'error'); }
    }'''),

        # 测试按钮
        ("showToast('邮箱配置已保存 (模拟)', 'success')",
         "testEmailSend()"),

        # 初始化（从 API 加载）
        ('''    document.addEventListener('DOMContentLoaded', () => {
      const s = MockData.settings;
      document.getElementById('smtpServer').value = s.email.smtpServer;''',
         '''    document.addEventListener('DOMContentLoaded', async () => {
      try {
        const res = await API.get('/settings');
        const s = res.data;
        document.getElementById('smtpServer').value = s.email.smtpServer || '';'''),

        ("s.email.smtpPort", "s.email.smtpPort || 587"),
        ("s.email.username", "s.email.username || ''"),
        ("s.email.senderName", "s.email.senderName || ''"),
        ("s.email.useTLS", "s.email.useTLS || false"),
        ("s.database.path", "s.database.path || ''"),
        ("s.database.backupEnabled", "s.database.backupEnabled || false"),
        ("s.database.backupInterval", "s.database.backupInterval || 'daily'"),
        ("s.storage.uploadFolder", "s.storage.uploadFolder || ''"),
        ("s.storage.maxFileSize / (1024 * 1024)", "(s.storage.maxFileSize || 10485760) / (1024 * 1024)"),
        ("s.storage.allowedTypes", "s.storage.allowedTypes || ''"),
        ("s.reminder.daysBefore", "s.reminder.daysBefore || 30"),
        ("s.reminder.sendTime", "s.reminder.sendTime || '09:00'"),
        ("s.reminder.recipients", "s.reminder.recipients || ''"),
        ("s.reminder.enabled", "s.reminder.enabled || false"),

        # 末尾加 catch
        ('''      document.getElementById('remindEnabled').checked = s.reminder.enabled;
    });''',
         '''      document.getElementById('remindEnabled').checked = s.reminder.enabled || false;
      } catch (err) { showToast('加载配置失败: ' + err.message, 'error'); }
    });'''),
    ]
    patch(path, pairs)
    # 添加 testEmailSend
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()
    add = '''\n    async function testEmailSend() {\n      const testEmail = prompt('输入测试接收邮箱:', document.getElementById('smtpUser').value);\n      if (!testEmail) return;\n      try { const res = await API.post('/settings/test-email', { email: testEmail }); showToast(res.message, 'success'); }\n      catch (err) { showToast('测试失败: ' + err.message, 'error'); }\n    }'''
    if 'function testEmailSend' not in c:
        c = c.replace('function saveSettings()', add + '\n\n    function saveSettings()')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)


# ==== export.html ====
def migrate_export():
    path = os.path.join(PAGES, 'export.html')
    # export.html 的 handleExport 已经在 app.js 中定义了但旧的还在，需要更新内嵌脚本
    pairs = [
        # 旧的 handleExport 被页面内嵌覆盖，需要更新
        ('''  <script src="../js/app.js"></script>
  <script>
    function toggleExportOption(type) {''',
         '''  <script src="../js/app.js"></script>
  <script>
    async function doExport() {
      const selected = document.querySelector('input[name="exportType"]:checked');
      if (!selected) { showToast('请选择导出方式', 'warning'); return; }
      const type = selected.value;
      const body = { type, format: 'json' };

      if (type === 'byCreate') {
        const s = document.getElementById('startCreate').value;
        const e = document.getElementById('endCreate').value;
        if (!s || !e) { showToast('请选择创建时间范围', 'warning'); return; }
        body.startDate = s; body.endDate = e;
      } else if (type === 'byExpire') {
        const s = document.getElementById('startExpire').value;
        const e = document.getElementById('endExpire').value;
        if (!s || !e) { showToast('请选择到期时间范围', 'warning'); return; }
        body.startDate = s; body.endDate = e;
      }

      try {
        const res = await API.post('/export', body);
        if (res.data) {
          const info = res.data.exportInfo;
          showToast('导出成功! 合同' + info.totalContracts + '条, 专利' + info.totalPatents + '条, 车险' + info.totalInsurances + '条', 'success');
        }
      } catch (err) { showToast('导出失败: ' + err.message, 'error'); }
    }

    function toggleExportOption(type) {'''),
    ]
    patch(path, pairs)
    # 更新按钮
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()
    c = c.replace("onclick=\"handleExport()\"", "onclick=\"doExport()\"")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)


if __name__ == '__main__':
    migrate_insurance()
    migrate_files()
    migrate_users()
    migrate_logs()
    migrate_settings()
    migrate_export()
    print('All done!')
