/* ============================================================
   素珍管理系统 - 全局 JS
   API 请求封装、Token 管理、导航、通用组件
   ============================================================ */

// ============================================================
// 配置
// ============================================================
// Docker 部署（nginx 代理）→ 相对路径 /api
// 本地开发（直接打开或 flask dev server）→ http://localhost:5000/api
const API_BASE = (window.location.port === '8080' || window.location.port === '80')
  ? '/api'
  : 'http://localhost:5000/api';

// ============================================================
// Token & 用户状态管理
// ============================================================
const Session = {
  _token: localStorage.getItem('suzhen_token') || '',
  _user: JSON.parse(localStorage.getItem('suzhen_user') || 'null'),

  get token() { return this._token; },
  get user() { return this._user; },
  get isLoggedIn() { return !!this._token; },

  save(token, user) {
    this._token = token;
    this._user = user;
    localStorage.setItem('suzhen_token', token);
    localStorage.setItem('suzhen_user', JSON.stringify(user));
  },

  clear() {
    this._token = '';
    this._user = null;
    localStorage.removeItem('suzhen_token');
    localStorage.removeItem('suzhen_user');
  },
};

// ============================================================
// HTTP 请求封装
// ============================================================
const API = {
  async request(method, path, opts = {}) {
    const url = API_BASE + path;
    const headers = {
      'Content-Type': 'application/json',
      ...(opts.headers || {}),
    };

    if (Session.token) {
      headers['Authorization'] = 'Bearer ' + Session.token;
    }

    // 文件上传时去掉 Content-Type 让浏览器自动设置 boundary
    if (opts.body instanceof FormData) {
      delete headers['Content-Type'];
    }

    try {
      const res = await fetch(url, {
        method,
        headers,
        body: opts.body instanceof FormData ? opts.body
          : (opts.body ? JSON.stringify(opts.body) : undefined),
      });

      const data = await res.json();

      if (!res.ok) {
        if (res.status === 401) {
          Session.clear();
          window.location.href = '../index.html';
          throw new Error('未登录或令牌过期');
        }
        throw new Error(data.message || `请求失败 (${res.status})`);
      }

      return data;
    } catch (err) {
      if (err.name === 'TypeError' && err.message.includes('fetch')) {
        throw new Error('无法连接到后端服务器，请确认后端已启动');
      }
      throw err;
    }
  },

  get(path, params = {}) {
    const qs = new URLSearchParams(params).toString();
    return this.request('GET', qs ? path + '?' + qs : path);
  },

  post(path, body) { return this.request('POST', path, { body }); },
  put(path, body) { return this.request('PUT', path, { body }); },
  del(path) { return this.request('DELETE', path); },

  upload(path, formData) {
    return this.request('POST', path, { body: formData });
  },

  download(path, filename) {
    const url = API_BASE + path;
    const link = document.createElement('a');
    link.href = url;
    link.download = filename || '';
    // 携带 token 用于鉴权（通过查询参数，因为 a 标签不能设置 header）
    link.href = url + (url.includes('?') ? '&' : '?') + 'token=' + encodeURIComponent(Session.token);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  },
};

// ============================================================
// 工具函数
// ============================================================

function getStatusBadge(status) {
  const map = {
    active: '<span class="badge active">生效中</span>',
    expired: '<span class="badge expired">已到期</span>',
    expiring: '<span class="badge expiring">即将到期</span>',
    pending: '<span class="badge pending">待审核</span>',
    inactive: '<span class="badge expired">已禁用</span>',
  };
  return map[status] || `<span class="badge">${status}</span>`;
}

function formatDate(dateStr) {
  if (!dateStr) return '-';
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) return dateStr;
  return `${d.getFullYear()}年${String(d.getMonth() + 1).padStart(2, '0')}月${String(d.getDate()).padStart(2, '0')}日`;
}

function formatFileSize(bytes) {
  if (typeof bytes === 'string') return bytes;
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function formatMoney(num) {
  return '¥' + Number(num).toLocaleString('zh-CN');
}

function isAdmin() {
  return Session.user && Session.user.role === '管理员';
}

function showToast(message, type = 'info') {
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = '0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

function confirmAction(message, onConfirm) {
  if (confirm(message)) {
    onConfirm();
  }
}

// ============================================================
// 侧边栏 & 导航控制
// ============================================================

function initSidebar() {
  const toggleBtn = document.getElementById('menuToggle');
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebarOverlay');

  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener('click', () => {
      sidebar.classList.toggle('open');
      if (overlay) overlay.classList.toggle('show');
    });
    if (overlay) {
      overlay.addEventListener('click', () => {
        sidebar.classList.remove('open');
        overlay.classList.remove('show');
      });
    }
  }
  highlightCurrentPage();
}

function highlightCurrentPage() {
  const currentPage = getCurrentPage();
  document.querySelectorAll('.sidebar .menu-item').forEach(item => {
    if (item.getAttribute('href') && item.getAttribute('href').includes(currentPage)) {
      item.classList.add('active');
    }
  });
  document.querySelectorAll('.navbar .nav-links a').forEach(link => {
    if (link.getAttribute('href') && link.getAttribute('href').includes(currentPage)) {
      link.classList.add('active');
    }
  });
}

function getCurrentPage() {
  const path = window.location.pathname;
  return path.substring(path.lastIndexOf('/') + 1) || 'dashboard.html';
}

function updateNavUser() {
  const userNameEl = document.getElementById('navUserName');
  const userAvatarEl = document.getElementById('navUserAvatar');
  if (userNameEl && Session.user) userNameEl.textContent = Session.user.displayName || Session.user.username;
  if (userAvatarEl && Session.user) userAvatarEl.textContent = (Session.user.displayName || Session.user.username).charAt(0);
}

function applyPermissions() {
  // 非管理员隐藏所有 admin-only 元素
  if (!isAdmin()) {
    document.querySelectorAll('.admin-only').forEach(el => el.style.display = 'none');
  }
}

// ============================================================
// 模态框
// ============================================================
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.add('show');
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove('show');
}

// ============================================================
// 登录逻辑 (对接后端 API)
// ============================================================

async function handleLogin(event) {
  event.preventDefault();
  const username = document.getElementById('username').value.trim();
  const password = document.getElementById('password').value.trim();
  const errorEl = document.getElementById('loginError');
  const btn = document.querySelector('button[type="submit"]');

  if (!username || !password) {
    if (errorEl) { errorEl.textContent = '请输入用户名和密码'; errorEl.style.display = 'block'; }
    return;
  }

  if (btn) { btn.disabled = true; btn.textContent = '登录中...'; }
  if (errorEl) errorEl.style.display = 'none';

  try {
    const res = await fetch(API_BASE + '/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.message || '登录失败');
    }

    Session.save(data.data.token, data.data.user);
    window.location.href = 'pages/dashboard.html';
  } catch (err) {
    if (errorEl) {
      errorEl.textContent = err.message || '登录失败，请检查网络连接';
      errorEl.style.display = 'block';
    }
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '登 录'; }
  }
}

// ============================================================
// 退出登录
// ============================================================

async function handleLogout() {
  if (confirm('确定要退出登录吗？')) {
    try {
      await API.post('/auth/logout');
    } catch (e) { /* ignore */ }
    Session.clear();
    window.location.href = '../index.html';
  }
}

// ============================================================
// 登录状态保护
// ============================================================

function requireLogin() {
  if (!Session.isLoggedIn) {
    window.location.href = '../index.html';
  }
}

// ============================================================
// 全局页面初始化
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
  // 非登录页需要鉴权
  if (!window.location.pathname.endsWith('login.html') &&
      !window.location.pathname.endsWith('index.html') &&
      window.location.pathname !== '/' &&
      window.location.pathname !== '') {
    requireLogin();
  }
  initSidebar();
  updateNavUser();
  applyPermissions();
});

// ============================================================
// 文件扫描助手（共享逻辑，供 contract/patent/insurance 页面使用）
// ============================================================
const ScanHelper = {
  // 当前扫描状态
  _state: {
    newFiles: [],
    currentDir: '',
    parentDir: null,
    subdirs: [],
    existingCount: 0,
    total: 0,
  },

  _module: '',
  _onImportComplete: null,
  _categoryProvider: null,

  /**
   * 初始化：设置模块名和回调
   * @param {string} module - 'contract' | 'patent' | 'insurance'
   * @param {Function} onImportComplete - 导入完成后的回调（刷新表格）
   * @param {Function} categoryProvider - 可选，返回分类字符串的函数（仅合同需要）
   */
  init(module, onImportComplete, categoryProvider) {
    this._module = module;
    this._onImportComplete = onImportComplete;
    this._categoryProvider = categoryProvider || null;
  },

  /** 打开同步模态框并重置状态 */
  openModal() {
    const dirInput = document.getElementById('syncDirectory');
    if (dirInput) dirInput.value = '';
    const resultDiv = document.getElementById('syncResult');
    if (resultDiv) resultDiv.innerHTML = '';
    const importBtn = document.getElementById('syncImportBtn');
    if (importBtn) importBtn.style.display = 'none';
    this._state = { newFiles: [], currentDir: '', parentDir: null, subdirs: [], existingCount: 0, total: 0 };
    openModal('syncModal');
  },

  /** 扫描目录 */
  async scanDirectory(dirOverride) {
    const dir = dirOverride || document.getElementById('syncDirectory').value.trim();
    if (!dir) { showToast('请输入目录路径', 'error'); return; }

    const btn = document.getElementById('syncScanBtn');
    btn.disabled = true;
    btn.textContent = '扫描中...';

    try {
      const res = await API.post('/scan', { directory: dir, module: this._module });
      const d = res.data;

      this._state.newFiles = d.newFiles;
      this._state.currentDir = d.currentDir || d.directory;
      this._state.parentDir = d.parentDir;
      this._state.subdirs = d.subdirs || [];
      this._state.existingCount = d.existingCount;
      this._state.total = d.total;

      this._renderResult(d);
    } catch (err) {
      showToast('扫描失败: ' + err.message, 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = '🔍 扫描';
    }
  },

  /** 导航到子目录 */
  navigateToSubdir(subdirName) {
    const newPath = this._state.currentDir + '/' + subdirName;
    document.getElementById('syncDirectory').value = newPath;
    this.scanDirectory(newPath);
  },

  /** 返回上级目录 */
  navigateUp() {
    if (this._state.parentDir) {
      document.getElementById('syncDirectory').value = this._state.parentDir;
      this.scanDirectory(this._state.parentDir);
    }
  },

  /** 渲染扫描结果 */
  _renderResult(d) {
    const container = document.getElementById('syncResult');
    let html = '';

    // ---- 面包屑导航 ----
    html += '<div style="margin-bottom:10px; font-size:12px; color:var(--text-muted); display:flex; align-items:center; gap:2px; flex-wrap:wrap;">';
    html += '<span>📍 </span>';
    const curDir = d.currentDir || d.directory;
    const parts = curDir.split('/').filter(function(p) { return p; });
    const clickableParts = [];
    for (var i = 0; i < parts.length; i++) {
      clickableParts.push(parts.slice(0, i + 1).join('/'));
    }
    html += '<a href="javascript:void(0)" onclick="ScanHelper._breadcrumbClick(\'/\')" style="color:var(--primary); text-decoration:none;">/</a>';
    for (var j = 0; j < parts.length; j++) {
      html += '<span style="color:var(--text-muted);">/</span>';
      html += '<a href="javascript:void(0)" onclick="ScanHelper._breadcrumbClick(\'' +
        clickableParts[j].replace(/'/g, "\\'") + '\')" style="color:var(--primary); text-decoration:none;">' +
        parts[j].replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</a>';
    }
    html += '</div>';

    // ---- 返回上级按钮 ----
    if (d.parentDir) {
      html += '<button class="btn btn-outline btn-sm" onclick="ScanHelper.navigateUp()" style="margin-bottom:8px;">⬆ 返回上级</button>';
    }

    // ---- 统计信息 ----
    html += '<div style="margin-bottom:8px; color:var(--text-muted); font-size:13px;">' +
      '当前目录共 ' + d.total + ' 个文件，其中 <b style="color:var(--success);">' +
      d.newCount + '</b> 个待导入，<b>' + d.existingCount + '</b> 个已存在</div>';

    // ---- 子目录列表 ----
    if (d.subdirs && d.subdirs.length > 0) {
      html += '<div style="margin-bottom:4px;"><strong style="font-size:12px;">📁 子目录：</strong></div>';
      html += '<div style="display:flex; flex-wrap:wrap; gap:6px; margin-bottom:12px;">';
      d.subdirs.forEach(function(sub) {
        html += '<button class="btn btn-outline btn-sm" onclick="ScanHelper.navigateToSubdir(\'' +
          sub.replace(/'/g, "\\'") + '\')">📁 ' +
          sub.replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</button>';
      });
      html += '</div>';
    }

    // ---- 文件列表表格 ----
    if (d.newFiles.length > 0) {
      html += '<table style="font-size:12px;"><thead><tr>';
      html += '<th style="width:36px;"><input type="checkbox" id="syncSelectAll" onchange="ScanHelper._toggleSelectAll(this)" title="全选/取消全选"></th>';
      html += '<th>文件名</th>';
      html += '<th style="width:80px;">大小</th>';
      html += '<th style="width:60px;">状态</th>';
      html += '</tr></thead><tbody>';
      d.newFiles.forEach(function(f, idx) {
        html += '<tr>' +
          '<td><input type="checkbox" class="syncFileCheck" value="' + idx + '" data-path="' +
          f.path.replace(/"/g, '&quot;') + '" data-name="' +
          f.name.replace(/"/g, '&quot;') + '"></td>' +
          '<td>📄 ' + f.name.replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</td>' +
          '<td>' + formatFileSize(f.size) + '</td>' +
          '<td><span class="badge active" style="font-size:10px;">待导入</span></td>' +
          '</tr>';
      });
      html += '</tbody></table>';
    } else if (d.total === 0 && (!d.subdirs || d.subdirs.length === 0)) {
      html += '<p style="color:var(--text-muted);">当前目录为空，未找到支持的文件</p>';
    }

    // ---- 已存在文件折叠区 ----
    if (d.existingFiles && d.existingFiles.length > 0) {
      html += '<details style="margin-top:8px; font-size:12px;">' +
        '<summary style="cursor:pointer; color:var(--text-muted);">已存在的文件 (' + d.existingFiles.length + ' 个)</summary>' +
        '<div style="max-height:150px; overflow-y:auto; margin-top:4px;">';
      d.existingFiles.forEach(function(f) {
        html += '<div style="font-size:11px; color:var(--text-muted); padding:2px 0;">📄 ' +
          f.name.replace(/</g, '&lt;').replace(/>/g, '&gt;') + ' (' + formatFileSize(f.size) + ')</div>';
      });
      html += '</div></details>';
    }

    container.innerHTML = html;

    // 显示/隐藏导入按钮
    var importBtn = document.getElementById('syncImportBtn');
    if (d.newFiles.length > 0) {
      importBtn.style.display = '';
    } else {
      importBtn.style.display = 'none';
    }
  },

  /** 全选/取消全选 */
  _toggleSelectAll(checkbox) {
    document.querySelectorAll('.syncFileCheck').forEach(function(cb) {
      cb.checked = checkbox.checked;
    });
  },

  /** 获取选中的文件列表 */
  _getSelectedFiles() {
    var checked = document.querySelectorAll('.syncFileCheck:checked');
    var result = [];
    for (var i = 0; i < checked.length; i++) {
      result.push({
        path: checked[i].getAttribute('data-path'),
        name: checked[i].getAttribute('data-name'),
      });
    }
    return result;
  },

  /** 面包屑点击导航 */
  _breadcrumbClick(dir) {
    document.getElementById('syncDirectory').value = dir;
    this.scanDirectory(dir);
  },

  /** 导入选中的文件 */
  async importFiles() {
    var selectedFiles = this._getSelectedFiles();
    if (selectedFiles.length === 0) {
      showToast('请至少选择一个文件', 'error');
      return;
    }

    var btn = document.getElementById('syncImportBtn');
    btn.disabled = true;
    btn.textContent = '导入中...';

    var category = '';
    if (this._categoryProvider) {
      category = this._categoryProvider();
    }

    try {
      var res = await API.post('/scan/import', {
        module: this._module,
        files: selectedFiles,
        category: category,
      });
      showToast(res.message, 'success');
      closeModal('syncModal');
      if (this._onImportComplete) {
        this._onImportComplete();
      }
    } catch (err) {
      showToast('导入失败: ' + err.message, 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = '📥 导入选中文件';
    }
  },
};
