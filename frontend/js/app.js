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
          window.location.href = '../login.html';
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
    window.location.href = '../login.html';
  }
}

// ============================================================
// 登录状态保护
// ============================================================

function requireLogin() {
  if (!Session.isLoggedIn) {
    window.location.href = '../login.html';
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
