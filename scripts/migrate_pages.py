"""批量迁移前端页面从 MockData 到真实 API"""
import re, os

PAGES = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'pages')

def replace_block(content, old, new):
    """安全替换，检查 old 出现一次"""
    count = content.count(old)
    if count == 0:
        return False, "old not found"
    if count > 1:
        return False, f"old found {count} times (ambiguous)"
    return True, content.replace(old, new)

def migrate_file(path, replacements):
    """对文件执行多个 (old, new) 替换"""
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    for old, new in replacements:
        content = content.replace(old, new)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return True

# ==========================================
# PATENT
# ==========================================
def migrate_patent():
    path = os.path.join(PAGES, 'patent.html')
    reps = [
        # filter → load
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
         '''    async function loadPatents(params = {}) {
      params.page = params.page || patentPage; params.pageSize = params.pageSize || patentPageSize;
      if (document.getElementById('filterPatentType').value) params.type = document.getElementById('filterPatentType').value;
      if (document.getElementById('filterPatentStatus').value) params.status = document.getElementById('filterPatentStatus').value;
      if (document.getElementById('patentSearch').value) params.keyword = document.getElementById('patentSearch').value;
      try { const res = await API.get('/patents', params); return res.data; }
      catch (err) { showToast('加载失败: ' + err.message, 'error'); return { items: [], total: 0 }; }
    }'''),

        # renderPatentTable 中 filtered → data
        ('''    function renderPatentTable() {
      const filtered = filterPatents();
      const totalPages = Math.ceil(filtered.length / patentPageSize);
      const start = (patentPage - 1) * patentPageSize;
      const pageData = filtered.slice(start, start + patentPageSize);
      const tbody = document.getElementById('patentTableBody');''',
         '''    async function renderPatentTable() {
      const data = await loadPatents();
      const tbody = document.getElementById('patentTableBody');'''),

        # 空数据判断
        ('''      if (pageData.length === 0) {''',
         '''      if (data.items.length === 0) {'''),

        # 数据行渲染
        ('''pageData.map(p => `''',
         '''data.items.map(p => `'''),

        # 字段名适配 (createTime → createdAt, expireTime → expireDate)
        ('''${p.createTime}''', '''${p.createdAt || p.createTime}'''),
        ('''${p.expireTime}''', '''${p.expireDate || p.expireTime}'''),

        # 分页
        ('''      const totalPages = Math.ceil(filtered.length / patentPageSize);''',
         '''      const totalPages = Math.ceil(data.total / patentPageSize);'''),

        # goPatentPage
        ('''    function goPatentPage(p) {
      const totalPages = Math.ceil(filterPatents().length / patentPageSize);
      if (p < 1 || p > totalPages) return;
      patentPage = p;
      renderPatentTable();
    }''',
         '''    function goPatentPage(p) { patentPage = p; renderPatentTable(); }'''),

        # editPatent
        ('''    function editPatent(id) {
      const p = MockData.patents.find(x => x.id === id); if (!p) return;''',
         '''    function editPatent(id) {
      API.get('/patents/' + id).then(res => { const p = res.data;'''),

        # editPatent 结尾 (openModal 之后)
        ('''      document.getElementById('patentCreateDate').value = p.createTime.substring(0, 10);
      document.getElementById('patentExpireDate').value = p.expireTime;
      document.getElementById('patentFilePath').value = p.filePath;
      document.getElementById('patentRemark').value = p.remark;
      openModal('patentModal');
    }''',
         '''      document.getElementById('patentCreateDate').value = (p.applicationDate || p.createdAt || p.createTime || '').substring(0, 10);
      document.getElementById('patentExpireDate').value = p.expireDate || p.expireTime;
      document.getElementById('patentFilePath').value = p.filePath || '';
      document.getElementById('patentRemark').value = p.remark || '';
      openModal('patentModal');
    }).catch(err => showToast('获取专利失败: ' + err.message, 'error'));
    }'''),

        # savePatent - 删除本地逻辑, 改为 API
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
    }'''),

        # viewPatent
        ('''    function viewPatent(id) {
      const p = MockData.patents.find(x => x.id === id); if (!p) return;''',
         '''    async function viewPatent(id) {
      try { const res = await API.get('/patents/' + id); const p = res.data;'''),

        # viewPatent 的字段 (createTime/expireTime → createdAt/expireDate)
        ('''          <div><strong>创建时间：</strong>${p.createTime}</div>
          <div><strong>到期时间：</strong>${p.expireTime}</div>''',
         '''          <div><strong>创建时间：</strong>${p.createdAt || p.createTime}</div>
          <div><strong>到期时间：</strong>${p.expireDate || p.expireTime}</div>'''),

        # viewPatent 缺少 catch
        ('''      openModal('patentDetailModal');
    }''',
         '''      openModal('patentDetailModal');
      } catch (err) { showToast('加载专利详情失败: ' + err.message, 'error'); }
    }'''),

        # renderPatents
        ('''    function renderPatents() { patentPage = 1; renderPatentTable(); }''',
         '''    function renderPatents() { patentPage = 1; renderPatentTable(); }'''),

        # 替换删除操作中的 MockData 引用
        ('''MockData.patents = MockData.patents.filter''',
         '''(async () => { try { await API.del('/patents/'''),
    ]
    migrate_file(path, reps)
    print('  patent.html done')


if __name__ == '__main__':
    migrate_patent()
    print('Migrate patent complete')
