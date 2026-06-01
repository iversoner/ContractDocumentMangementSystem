"""一次性批量替换所有页面的 MockData → API 调用"""
import os, re

PAGES = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'pages')

def patch_file(filename, patches):
    """对文件执行一系列 (old_snippet, new_snippet, count_hint) 替换"""
    path = os.path.join(PAGES, filename)
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()
    for old, new, expect in patches:
        actual = c.count(old)
        if actual != expect:
            print(f"  WARN {filename}: '{old[:40]}...' expected {expect} found {actual}")
        c = c.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(c)
    print(f"  OK {filename}")


# ==== patent.html ====
patch_file('patent.html', [
    # filterPatents → loadPatents
    ('''    function filterPatents() {
      const type = document.getElementById('filterPatentType').value;
      const status = document.getElementById('filterPatentStatus').value;
      const kw = document.getElementById('patentSearch').value.toLowerCase();
      return MockData.patents.filter(p => {
        if (type && p.type !== type) return false;
        if (status && p.status !== status) return false;
        if (kw && !p.name.toLowerCase().includes(kw) && !p.patentNo.toLowerCase().includes(kw)) return false;
        return true;
      });
    }''',
     '''    async function loadPatents() {
      const params = { page: patentPage, pageSize: patentPageSize };
      if (document.getElementById('filterPatentType').value) params.type = document.getElementById('filterPatentType').value;
      if (document.getElementById('filterPatentStatus').value) params.status = document.getElementById('filterPatentStatus').value;
      if (document.getElementById('patentSearch').value) params.keyword = document.getElementById('patentSearch').value;
      try { const res = await API.get('/patents', params); return res.data; }
      catch (err) { showToast('加载失败: ' + err.message, 'error'); return { items: [], total: 0 }; }
    }''', 1),

    # renderPatentTable 开头
    ('''    function renderPatentTable() {
      const filtered = filterPatents();
      const totalPages = Math.ceil(filtered.length / patentPageSize);
      const start = (patentPage - 1) * patentPageSize;
      const pageData = filtered.slice(start, start + patentPageSize);
      const tbody = document.getElementById('patentTableBody');''',
     '''    async function renderPatentTable() {
      const data = await loadPatents();
      const tbody = document.getElementById('patentTableBody');''', 1),

    # pageData/n_items → data.items
    ("pageData.length === 0", "data.items.length === 0", 2),
    ("pageData.map(p =>", "data.items.map(p =>", 1),
    ("filtered.length / patentPageSize", "data.total / patentPageSize", 1),

    # 字段名适配
    ("${p.createTime}", "${p.createdAt || p.createTime}", 3),
    ("${p.expireTime}", "${p.expireDate || p.expireTime}", 3),
    ("p.createTime.substring(0, 10)", "(p.applicationDate || p.createdAt || '').substring(0, 10)", 1),

    # goPatentPage
    ('''    function goPatentPage(p) {
      const totalPages = Math.ceil(filterPatents().length / patentPageSize);
      if (p < 1 || p > totalPages) return;
      patentPage = p;
      renderPatentTable();
    }''',
     '''    function goPatentPage(p) { patentPage = p; renderPatentTable(); }''', 1),

    # editPatent
    ("    function editPatent(id) {\n      const p = MockData.patents.find(x => x.id === id); if (!p) return;",
     "    function editPatent(id) {\n      API.get('/patents/' + id).then(res => { const p = res.data;", 1),
    ("      document.getElementById('patentFilePath').value = p.filePath;\n      document.getElementById('patentRemark').value = p.remark;\n      openModal('patentModal');\n    }",
     "      document.getElementById('patentFilePath').value = p.filePath || '';\n      document.getElementById('patentRemark').value = p.remark || '';\n      openModal('patentModal');\n    }).catch(err => showToast('获取专利失败: ' + err.message, 'error'));\n    }", 1),

    # savePatent — 整体替换
    ('''    function savePatent(e) {
      e.preventDefault();
      const id = document.getElementById('patentId').value;
      const now = new Date().toISOString().replace('T', ' ').substring(0, 19);
      const expDate = document.getElementById('patentExpireDate').value;
      const today = new Date().toISOString().substring(0, 10);
      let status = 'active';
      if (expDate < today) status = 'expired';

      const data = {
        id: id ? parseInt(id) : Math.max(...MockData.patents.map(x => x.id), 0) + 1,
        name: document.getElementById('patentName').value,
        patentNo: document.getElementById('patentNo').value,
        type: document.getElementById('patentType').value,
        holder: document.getElementById('patentHolder').value,
        agent: document.getElementById('patentAgent').value,
        createTime: id ? MockData.patents.find(x => x.id === parseInt(id)).createTime : now,
        expireTime: expDate,
        status: status,
        filePath: document.getElementById('patentFilePath').value || `/files/patent_new.pdf`,
        remark: document.getElementById('patentRemark').value,
      };

      if (id) {
        MockData.patents[MockData.patents.findIndex(x => x.id === parseInt(id))] = data;
        showToast('专利已更新', 'success');
      } else {
        MockData.patents.unshift(data);
        showToast('专利已添加', 'success');
      }
      closeModal('patentModal');
      renderPatentTable();
    }''',
     '''    async function savePatent(e) {
      e.preventDefault();
      const id = document.getElementById('patentId').value;
      const body = {
        name: document.getElementById('patentName').value,
        patentNo: document.getElementById('patentNo').value,
        type: document.getElementById('patentType').value,
        holder: document.getElementById('patentHolder').value,
        agent: document.getElementById('patentAgent').value,
        applicationDate: document.getElementById('patentCreateDate').value,
        expireDate: document.getElementById('patentExpireDate').value,
        filePath: document.getElementById('patentFilePath').value,
        remark: document.getElementById('patentRemark').value,
      };
      try {
        if (id) { await API.put('/patents/' + id, body); showToast('专利已更新', 'success'); }
        else { await API.post('/patents', body); showToast('专利已添加', 'success'); }
        closeModal('patentModal'); renderPatentTable();
      } catch (err) { showToast('保存失败: ' + err.message, 'error'); }
    }''', 1),

    # viewPatent
    ("    function viewPatent(id) {\n      const p = MockData.patents.find(x => x.id === id); if (!p) return;",
     "    async function viewPatent(id) {\n      try { const res = await API.get('/patents/' + id); const p = res.data;", 1),
    ("      openModal('patentDetailModal');\n    }",
     "      openModal('patentDetailModal');\n      } catch (err) { showToast('加载详情失败: ' + err.message, 'error'); }\n    }", 1),

    # 删除操作
    ("MockData.patents = MockData.patents.filter(x => x.id !== ${p.id}); renderPatentTable();",
     "await API.del('/patents/' + p.id); renderPatentTable();", 1),
    # sync 删除按钮回调
    ("onclick=\"confirmAction('确定删除专利「${p.name}」吗？', () => { MockData.patents = MockData.patents.filter(x => x.id !== ${p.id}); renderPatentTable(); })\"",
     "onclick=\"deletePatent(${p.id}, '${p.name.replace(/'/g, \"\\\\'\")}')\"", 1),
])

# 添加 deletePatent 函数到 patent.html（在 goPatentPage 之后）
path = os.path.join(PAGES, 'patent.html')
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()
add_fn = '''\n    async function deletePatent(id, name) {\n      if (!confirm('确定删除专利「' + name + '」吗？')) return;\n      try { await API.del('/patents/' + id); showToast('专利已删除', 'success'); renderPatentTable(); }\n      catch (err) { showToast('删除失败: ' + err.message, 'error'); }\n    }'''
if 'function deletePatent' not in c:
    c = c.replace('function goPatentPage(p)', 'function goPatentPage(p)' + add_fn)
with open(path, 'w', encoding='utf-8') as f:
    f.write(c)

print('  patent.html: added deletePatent')
print('Batch migrate complete!')
