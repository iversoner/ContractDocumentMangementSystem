"""
将前端页面从 MockData 迁移到真实 API 调用
批量替换嵌入脚本中的逻辑
"""
import re
import os

FRONTEND_PAGES = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'pages')


def migrate_contract(filepath):
    """合同页面迁移"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 替换整个内嵌脚本
    old_script = r'''  <script src="../js/app.js"></script>
  <script>
    let currentPage = 1;
    const pageSize = 8;'''

    new_script = '''  <script src="../js/app.js"></script>
  <script>
    let currentPage = 1;
    const pageSize = 8;

    // ---- API 调用 ----
    async function loadContracts(params = {}) {
      params.page = params.page || currentPage;
      params.pageSize = params.pageSize || pageSize;
      const cat = document.getElementById('filterCategory').value;
      const st = document.getElementById('filterStatus').value;
      const kw = document.getElementById('searchKeyword').value;
      if (cat) params.category = cat;
      if (st) params.status = st;
      if (kw) params.keyword = kw;
      try {
        const res = await API.get('/contracts', params);
        return res.data;
      } catch (err) {
        showToast('加载失败: ' + err.message, 'error');
        return { items: [], total: 0 };
      }
    }

    function renderContracts() { currentPage = 1; renderTable(); }

    async function renderTable() {
      const data = await loadContracts();
      const tbody = document.getElementById('contractTableBody');
      if (data.items.length === 0) {
        tbody.innerHTML = `<tr><td colspan="11" style="text-align:center; padding:40px; color:var(--text-muted);">暂无数据</td></tr>`;
      } else {
        tbody.innerHTML = data.items.map(c => `
          <tr>
            <td>${c.id}</td>
            <td><a href="javascript:viewContract(${c.id})">${c.name}</a></td>
            <td>${c.category}</td>
            <td>${c.company}</td>
            <td>${c.agent}</td>
            <td>${c.createdAt || c.createTime}</td>
            <td>${c.endDate || c.expireTime}</td>
            <td>${getStatusBadge(c.status)}</td>
            <td><a href="javascript:void(0)" onclick="showToast('文件: ${c.filePath || '(无)'}', 'info')">📎 查看</a></td>
            <td>${c.remark || '-'}</td>
            <td>
              <button class="btn btn-outline btn-sm" onclick="editContract(${c.id})">编辑</button>
              <button class="btn btn-danger btn-sm" onclick="deleteContract(${c.id}, '${c.name.replace(/'/g, '\\\\\'')}')">删除</button>
            </td>
          </tr>
        `).join('');
      }
      // 分页
      const totalPages = Math.ceil(data.total / pageSize);
      const pag = document.getElementById('contractPagination');
      if (totalPages <= 1) { pag.innerHTML = ''; } else {
        let html = `<button class="page-btn" onclick="goPage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''}>&laquo;</button>`;
        for (let i = 1; i <= totalPages; i++) {
          html += `<button class="page-btn ${i === currentPage ? 'active' : ''}" onclick="goPage(${i})">${i}</button>`;
        }
        html += `<button class="page-btn" onclick="goPage(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''}>&raquo;</button>`;
        pag.innerHTML = html;
      }
    }

    function goPage(p) { currentPage = p; renderTable(); }

    async function deleteContract(id, name) {
      if (!confirm('确定删除合同「' + name + '」吗？')) return;
      try { await API.del('/contracts/' + id); showToast('合同已删除', 'success'); renderTable(); }
      catch (err) { showToast('删除失败: ' + err.message, 'error'); }
    }

    function openContractModal() {
      document.getElementById('contractModalTitle').textContent = '新增合同';
      ['contractId','contractName','contractCategory','contractCompany','contractAgent','contractContact','contractContactPhone','contractContactEmail','contractStartDate','contractEndDate','contractFilePath','contractRemark'].forEach(id => {
        document.getElementById(id).value = '';
      });
      openModal('contractModal');
    }

    async function editContract(id) {
      try {
        const res = await API.get('/contracts/' + id);
        const c = res.data;
        document.getElementById('contractModalTitle').textContent = '编辑合同';
        document.getElementById('contractId').value = c.id;
        document.getElementById('contractName').value = c.name;
        document.getElementById('contractCategory').value = c.category;
        document.getElementById('contractCompany').value = c.company;
        document.getElementById('contractAgent').value = c.agent;
        document.getElementById('contractContact').value = c.contactPerson || '';
        document.getElementById('contractContactPhone').value = c.contactPhone || '';
        document.getElementById('contractContactEmail').value = c.contactEmail || '';
        document.getElementById('contractStartDate').value = c.startDate;
        document.getElementById('contractEndDate').value = c.endDate;
        document.getElementById('contractFilePath').value = c.filePath || '';
        document.getElementById('contractRemark').value = c.remark || '';
        openModal('contractModal');
      } catch (err) {
        showToast('获取合同详情失败: ' + err.message, 'error');
      }
    }

    async function saveContract(e) {
      e.preventDefault();
      const id = document.getElementById('contractId').value;
      const body = {
        name: document.getElementById('contractName').value,
        category: document.getElementById('contractCategory').value,
        company: document.getElementById('contractCompany').value,
        contactPerson: document.getElementById('contractContact').value,
        contactPhone: document.getElementById('contractContactPhone').value,
        contactEmail: document.getElementById('contractContactEmail').value,
        agent: document.getElementById('contractAgent').value,
        startDate: document.getElementById('contractStartDate').value,
        endDate: document.getElementById('contractEndDate').value,
        filePath: document.getElementById('contractFilePath').value,
        remark: document.getElementById('contractRemark').value,
      };
      try {
        if (id) { await API.put('/contracts/' + id, body); showToast('合同已更新', 'success'); }
        else { await API.post('/contracts', body); showToast('合同已添加', 'success'); }
        closeModal('contractModal');
        renderTable();
      } catch (err) {
        showToast('保存失败: ' + err.message, 'error');
      }
    }

    async function viewContract(id) {
      try {
        const res = await API.get('/contracts/' + id);
        const c = res.data;
        document.getElementById('detailContent').innerHTML = `
          <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; font-size:13px;">
            <div><strong>合同名称：</strong>${c.name}</div>
            <div><strong>类别：</strong>${c.category}</div>
            <div><strong>合同公司：</strong>${c.company}</div>
            <div><strong>联系人：</strong>${c.contactPerson || '-'}</div>
            <div><strong>联系人电话：</strong>${c.contactPhone || '-'}</div>
            <div><strong>对接业务员：</strong>${c.agent}</div>
            <div><strong>联系人邮箱：</strong>${c.contactEmail || '-'}</div>
            <div><strong>开始日期：</strong>${c.startDate}</div>
            <div><strong>到期日期：</strong>${c.endDate}</div>
            <div><strong>状态：</strong>${getStatusBadge(c.status)}</div>
            <div><strong>创建时间：</strong>${c.createdAt}</div>
            <div><strong>文件路径：</strong>${c.filePath || '无'}</div>
            <div style="grid-column: 1/-1;"><strong>备注：</strong>${c.remark || '无'}</div>
          </div>
        `;
        openModal('detailModal');
      } catch (err) { showToast('加载详情失败: ' + err.message, 'error'); }
    }

    document.addEventListener('DOMContentLoaded', renderTable);'''

    # 找到从 <script src...> 开始到 </script> 结束的整个块
    start_marker = '<script src="../js/app.js"></script>'
    end_marker = '</script>\n</body>'

    start_idx = content.find(start_marker)
    end_idx = content.rfind(end_marker)

    if start_idx == -1:
        print(f"  WARN: cannot find start marker in {filepath}")
        return

    new_content = content[:start_idx] + new_script + '\n</body>\n</html>\n'

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"  OK: {os.path.basename(filepath)}")


def migrate_simple_crud(filepath, api_path, title_label, fields_config):
    """
    通用 CRUD 页面迁移
    api_path: 如 'patents'
    title_label: 如 '专利'
    fields_config: 表单字段映射
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 这个函数暂时用更简单的方式——只处理模式相同的文件
    # 对于 patent, insurance, user 等，结构类似
    pass


if __name__ == '__main__':
    pages_dir = FRONTEND_PAGES
    migrate_contract(os.path.join(pages_dir, 'contract.html'))
