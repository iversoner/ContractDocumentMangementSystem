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
    const sep = url.includes('?') ? '&' : '?';
    const downloadUrl = url + sep + 'token=' + encodeURIComponent(Session.token);
    fetch(downloadUrl)
      .then(res => {
        if (!res.ok) throw new Error('下载失败');
        return res.blob();
      })
      .then(blob => {
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = filename || '';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        URL.revokeObjectURL(link.href);
      })
      .catch(err => showToast('下载失败: ' + err.message, 'error'));
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
// 统一弹窗方法（屏幕中央，蓝色主题）
// ============================================================

/**
 * 显示蓝色主题弹窗
 * @param {string} id - 弹窗唯一ID，用于关闭
 * @param {object} opts - { icon, title, body, footer, width }
 *   icon: 顶部图标（如 '⏳' '✅' '❌' '📋'），可选
 *   title: 标题文字
 *   body: HTML 字符串
 *   footer: HTML 字符串（默认 "确定" 按钮）
 *   width: 弹窗宽度（默认 460px）
 *   closable: 是否可点遮罩关闭（默认 false）
 */
function showBlueDialog(id, opts) {
  opts = opts || {};
  closeBlueDialog(id);

  var backdrop = document.createElement('div');
  backdrop.className = 'modal-backdrop show';
  backdrop.id = id;
  backdrop.style.zIndex = '9999';
  if (opts.closable) {
    backdrop.onclick = function(e) { if (e.target === backdrop) closeBlueDialog(id); };
  }

  var w = opts.width || '460px';
  var box = document.createElement('div');
  box.style.cssText = 'background:#fff;border-radius:12px;box-shadow:0 8px 40px rgba(24,144,255,0.2);width:90%;max-width:' + w + ';padding:0;overflow:hidden;';

  // Header
  var header = document.createElement('div');
  header.style.cssText = 'background:linear-gradient(135deg,#1890ff,#096dd9);color:#fff;padding:20px 24px;text-align:center;';
  var iconHtml = opts.icon ? '<div style="font-size:36px;margin-bottom:8px;">' + opts.icon + '</div>' : '';
  header.innerHTML = iconHtml + '<h3 style="margin:0;font-weight:600;">' + (opts.title || '') + '</h3>';
  box.appendChild(header);

  // Body
  var body = document.createElement('div');
  body.style.cssText = 'padding:24px;';
  body.innerHTML = opts.body || '';
  box.appendChild(body);

  // Footer
  var footer = document.createElement('div');
  footer.style.cssText = 'padding:16px 24px;border-top:1px solid #f0f0f0;text-align:right;';
  footer.innerHTML = opts.footer || '<button class="btn btn-primary" onclick="closeBlueDialog(\'' + id + '\')" style="min-width:100px;">确定</button>';
  box.appendChild(footer);

  backdrop.appendChild(box);
  document.body.appendChild(backdrop);
}

function closeBlueDialog(id) {
  var el = document.getElementById(id);
  if (el) el.remove();
}

/** 显示文件路径弹窗 */
function showFilePathDialog(filePath) {
  showBlueDialog('filePathDlg', {
    icon: '📁', title: '文件路径',
    body: '<div style="background:#f5f5f5;border-radius:6px;padding:16px;text-align:center;word-break:break-all;font-family:Consolas,monospace;font-size:13px;color:#333;">' + (filePath||'无').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') + '</div>' +
      '<p style="margin-top:12px;font-size:12px;color:#999;text-align:center;">请在文件管理器中打开上述路径查看文件</p>',
    footer: '<button class="btn btn-primary" onclick="closeBlueDialog(\'filePathDlg\')" style="min-width:100px;">确定</button>'
  });
}

// Spinner animation
(function() {
  if (document.getElementById('_blueDialogSpin')) return;
  var s = document.createElement('style');
  s.id = '_blueDialogSpin';
  s.textContent = '@keyframes spin { to { transform: rotate(360deg); } }';
  document.head.appendChild(s);
})();

// Sortable table header styles
(function() {
  if (document.getElementById('_sortableThStyle')) return;
  var s = document.createElement('style');
  s.id = '_sortableThStyle';
  s.textContent = '.sortable-th { cursor: pointer; user-select: none; white-space: nowrap; } .sortable-th:hover { background: #f0f5ff; } .sort-icon { font-size: 11px; margin-left: 2px; color: #ccc; }';
  document.head.appendChild(s);
})();

// ============================================================
// 信息完整性
// ============================================================
function getIsCompleteBadge(isComplete) {
  if (isComplete) {
    return '<span style="color:var(--success); cursor:default;" title="信息完整">✅ 完整</span>';
  }
  return '<span style="color:var(--warning); cursor:default;" title="信息不完整，请补充必填字段">⚠️ 不完整</span>';
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
  _state: {
    subdirs: [],
    checkedDirs: new Set(),
    loading: false,
  },

  _module: '',
  _onImportComplete: null,
  _categoryProvider: null,

  init(module, onImportComplete, categoryProvider) {
    this._module = module;
    this._onImportComplete = onImportComplete;
    this._categoryProvider = categoryProvider || null;
  },

  /** 打开同步模态框并自动扫描 /data */
  async openModal() {
    openModal('syncModal');
    this._state = { subdirs: [], checkedDirs: new Set(), loading: true };
    this._renderTree([], true);
    await this._scan('/data');
  },

  /** 扫描目录 */
  async _scan(dir) {
    try {
      const res = await API.post('/scan', { directory: dir, module: this._module });
      const d = res.data;
      this._state.subdirs = d.subdirs;
      this._state.loading = false;
      this._renderTree(d.subdirs, false, d.currentDir, d.parentDir, d.newCount);
    } catch (err) {
      this._state.loading = false;
      this._renderTree([], false);
      showToast('扫描失败: ' + err.message, 'error');
    }
  },

  /** 进入子目录 */
  enterDir(dirPath) {
    this._state.loading = true;
    this._state.subdirs = [];
    this._renderTree([], true);
    this._scan(dirPath);
  },

  /** 返回上级 */
  goUp() {
    const parent = document.getElementById('syncCurrentDir').getAttribute('data-parent');
    if (parent) {
      this._state.loading = true;
      this._state.subdirs = [];
      this._renderTree([], true);
      this._scan(parent);
    }
  },

  /** 返回根目录 /data */
  goRoot() {
    this._state.loading = true;
    this._state.subdirs = [];
    this._renderTree([], true);
    this._scan('/data');
  },

  /** 渲染目录树 */
  _renderTree(subdirs, loading, currentDir, parentDir, rootNewCount) {
    const container = document.getElementById('syncResult');
    if (!container) return;

    // 更新当前目录信息
    const dirInfo = document.getElementById('syncCurrentDir');
    if (dirInfo && currentDir) {
      dirInfo.textContent = currentDir;
      dirInfo.setAttribute('data-parent', parentDir || '');
    }
    if (dirInfo && rootNewCount !== undefined) {
      document.getElementById('syncNewBadge').textContent = rootNewCount;
      document.getElementById('syncNewBadge').style.display = rootNewCount > 0 ? '' : 'none';
    }

    if (loading) {
      container.innerHTML = '<p style="text-align:center; color:var(--text-muted); padding:20px;">⏳ 正在扫描目录...</p>';
      return;
    }

    let html = '';

    // 只显示有未导入文件的目录
    const dirsWithNew = subdirs.filter(function(d) { return d.newCount > 0; });
    const dirsNoNew = subdirs.filter(function(d) { return d.newCount === 0; });

    if (dirsWithNew.length === 0 && dirsNoNew.length === 0) {
      html += '<p style="text-align:center; color:var(--text-muted); padding:20px;">当前目录下没有子目录，或所有文件已录入系统</p>';
    } else {
      html += '<table style="font-size:12px; width:100%;"><thead><tr>';
      html += '<th style="width:36px;"><input type="checkbox" id="syncSelectAllDirs" onchange="ScanHelper._toggleAllDirs(this)"></th>';
      html += '<th>目录</th>';
      html += '<th style="width:80px;">未导入</th>';
      html += '<th style="width:60px;"></th>';
      html += '</tr></thead><tbody>';

      // 有新文件的目录
      dirsWithNew.forEach(function(d) {
        html += '<tr style="background:#f0fff0;">' +
          '<td><input type="checkbox" class="syncDirCheck" data-path="' + d.path.replace(/"/g, '&quot;') + '" onchange="ScanHelper._updateChecked()"' +
          (ScanHelper._state.checkedDirs.has(d.path) ? ' checked' : '') + '></td>' +
          '<td>📁 <b>' + d.name.replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</b></td>' +
          '<td><span class="badge active" style="font-size:10px;">' + d.newCount + ' 个</span></td>' +
          '<td><button class="btn btn-outline btn-sm" onclick="ScanHelper.enterDir(\'' + d.path.replace(/'/g, "\\'") + '\')" style="font-size:11px; padding:2px 6px;">📂 进入</button></td>' +
          '</tr>';
      });

      // 没有新文件的目录（折叠显示）
      if (dirsNoNew.length > 0) {
        html += '<tr><td colspan="4" style="padding:4px 0;">' +
          '<details style="font-size:11px;">' +
          '<summary style="cursor:pointer; color:var(--text-muted);">已全部导入的目录 (' + dirsNoNew.length + ' 个)</summary>';
        dirsNoNew.forEach(function(d) {
          html += '<div style="padding:2px 20px; color:var(--text-muted); display:flex; justify-content:space-between;">' +
            '<span>📁 ' + d.name.replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</span>' +
            '<button class="btn btn-outline btn-sm" onclick="ScanHelper.enterDir(\'' + d.path.replace(/'/g, "\\'") + '\')" style="font-size:11px; padding:2px 6px;">📂 进入</button>' +
            '</div>';
        });
        html += '</details></td></tr>';
      }

      html += '</tbody></table>';
    }

    container.innerHTML = html;

    // 恢复已勾选状态
    this._restoreChecks();

    var importBtn = document.getElementById('syncImportBtn');
    if (importBtn) {
      importBtn.style.display = this._state.checkedDirs.size > 0 ? '' : 'none';
    }
  },

  /** 全选/取消所有有新文件的目录 */
  _toggleAllDirs(cb) {
    var self = this;
    if (cb.checked) {
      document.querySelectorAll('.syncDirCheck').forEach(function(c) {
        c.checked = true;
        self._state.checkedDirs.add(c.getAttribute('data-path'));
      });
    } else {
      document.querySelectorAll('.syncDirCheck').forEach(function(c) {
        c.checked = false;
        self._state.checkedDirs.delete(c.getAttribute('data-path'));
      });
    }
    this._updateChecked();
  },

  /** 恢复已保存的勾选状态 */
  _restoreChecks() {
    var self = this;
    document.querySelectorAll('.syncDirCheck').forEach(function(c) {
      c.checked = self._state.checkedDirs.has(c.getAttribute('data-path'));
    });
    var allCb = document.getElementById('syncSelectAllDirs');
    if (allCb) {
      var all = document.querySelectorAll('.syncDirCheck');
      if (all.length > 0) {
        allCb.checked = Array.from(all).every(function(c) { return c.checked; });
      }
    }
  },

  /** 更新勾选状态 */
  _updateChecked() {
    var self = this;
    document.querySelectorAll('.syncDirCheck').forEach(function(c) {
      if (c.checked) {
        self._state.checkedDirs.add(c.getAttribute('data-path'));
      } else {
        self._state.checkedDirs.delete(c.getAttribute('data-path'));
      }
    });
    var importBtn = document.getElementById('syncImportBtn');
    if (importBtn) {
      importBtn.style.display = self._state.checkedDirs.size > 0 ? '' : 'none';
    }
    var allCb = document.getElementById('syncSelectAllDirs');
    if (allCb) {
      var all = document.querySelectorAll('.syncDirCheck');
      if (all.length > 0) {
        allCb.checked = Array.from(all).every(function(c) { return c.checked; });
      }
    }
  },

  /** 导入选中的目录 */
  async importDirs() {
    var dirs = Array.from(this._state.checkedDirs);
    if (dirs.length === 0) {
      showToast('请至少选择一个目录', 'error');
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
      var res = await API.post('/scan/import-dirs', {
        module: this._module,
        dirs: dirs,
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
      btn.textContent = '📥 导入选中目录';
    }
  },
};
