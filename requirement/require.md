# 素珍管理系统 - 需求文档

## 项目背景

构建一个基于 Python 的公司综合管理系统，用于管理公司的租赁、知识产权、合同、专利、车险续期等服务。系统采用全栈 Web 架构，支持 Docker 容器化一键部署。

---

## 功能模块

### 1. 用户认证
- 登录/登出系统
- 初始管理员账号: admin / admin!
- JWT Token 鉴权（24小时有效）
- 角色管理：管理员 / 业务员

### 2. 仪表盘
- 统计概览卡片（合同/专利/车险/文件/用户数量、生效中/即将到期/已到期统计）
- 到期提醒横幅
- 最近添加项目列表（跨模块合并排序）
- 即将到期项目列表

### 3. 合同管理
- 字段：合同名称、类别、合同公司、对接业务员、联系人、联系人电话、联系人邮箱、创建时间、到期时间、状态、本地文件链接、备注、邮件提醒（默认开启）、重要等级（重要/普通/不重要，默认普通）
- 增删改查操作
- 类别/状态/关键词筛选（手动搜索按钮提交）
- 分页展示
- 详情弹窗
- 邮件提醒列：每条记录可单独开关，关闭后到期提醒邮件跳过该条
- 重要等级列：彩色标签展示（重要=红色、普通=灰色、不重要=绿色）
- 批量操作：全选/批量设置邮件提醒/批量设置重要等级
- 可配置列显示：通过"列显示"按钮勾选要显示的列，配置保存到 localStorage，默认显示：名称、类别、公司、业务员、到期时间、状态、备注

### 4. 专利管理
- 字段：专利名称、专利号、类型、权利人、对接业务员、创建时间、到期时间、状态、本地文件链接、备注、邮件提醒（默认开启）、重要等级（重要/普通/不重要，默认普通）
- 增删改查操作
- 类型/状态/关键词筛选（手动搜索按钮提交）
- 分页展示
- 详情弹窗
- 邮件提醒列：每条记录可单独开关，关闭后到期提醒邮件跳过该条
- 重要等级列：彩色标签展示（重要=红色、普通=灰色、不重要=绿色）
- 批量操作：全选/批量设置邮件提醒/批量设置重要等级
- 可配置列显示：通过"列显示"按钮勾选要显示的列，配置保存到 localStorage，默认显示：名称、类别、公司、业务员、到期时间、状态、备注

### 5. 车险续期管理
- 字段：车牌号、品牌型号、保险公司、险种、保费金额、对接业务员、创建时间、到期时间、状态、本地文件链接、备注、邮件提醒（默认开启）、重要等级（重要/普通/不重要，默认普通）
- 增删改查操作
- 状态/保险公司/关键词筛选（手动搜索按钮提交）
- 页面级统计卡片（总数、生效中、即将到期、已过期，实时从 API 获取）
- 分页展示
- 邮件提醒列：每条记录可单独开关，关闭后到期提醒邮件跳过该条
- 重要等级列：彩色标签展示（重要=红色、普通=灰色、不重要=绿色）
- 批量操作：全选/批量设置邮件提醒/批量设置重要等级
- 可配置列显示：通过"列显示"按钮勾选要显示的列，配置保存到 localStorage，默认显示：名称、类别、公司、业务员、到期时间、状态、备注

### 6. 文件管理
- 文件类别固定可选：合同、专利、车险续期
- 文件上传/下载/删除
- 类别/关键词筛选
- 文件大小限制（默认10MB，可配置）
- 物理文件存储与数据库记录联动

### 7. 用户管理（管理员专用）
- 用户增删改查
- 角色筛选
- 重置密码
- 权限控制：管理员可查看所有用户；业务员/财务只能看到同角色用户

### 8. 系统配置（管理员专用）
- 邮箱服务配置（SMTP服务器/端口/账号/密码/TLS）
- 数据库配置
- 到期提醒配置（提前天数/发送时间/接收邮箱/启用开关）
- 文件存储配置（上传路径/最大文件大小/允许类型）
- 测试邮件发送

### 9. 系统日志
- 所有操作自动记录（时间、用户、操作、模块、级别、详情、IP地址）
- 级别筛选（信息/警告/错误）
- 模块筛选（认证、合同管理、专利管理、车险续期、文件管理、系统配置、邮件服务、数据导出）
- 关键词搜索
- 清空日志（管理员专用）
- 权限控制：管理员可查看所有日志；业务员/财务只能看到自己的日志

### 10. 数据导出
- 三种导出方式：导出所有数据 / 按创建时间范围导出 / 按到期时间范围导出
- 支持 JSON 和 CSV 格式

### 11. 目录扫描 & 批量导入
- 扫描指定目录下的文件，识别哪些文件尚未录入系统
- 支持合同、专利、车险三种模块
- 一键批量导入未录入的文件
- 文件路径去重，避免重复录入

---

## 技术栈

| 层级 | 技术选型 |
|------|----------|
| 后端 | Python 3.11+ / Flask 3.x |
| 前端 | HTML5 / CSS3 / Vanilla JavaScript |
| 数据库 | SQLite3 (WAL模式) |
| 文件存储 | 本地文件夹 |
| 邮件服务 | SMTP |
| 容器化 | Docker + Docker Compose |
| Web服务器 | Nginx (前端) + Gunicorn (后端) |

---

## 页面布局要求

每个管理页面必须包含：
- **导航栏 (Navbar)**：顶部固定，展示系统名称和所有功能模块快捷链接
- **侧边栏 (Sidebar)**：左侧固定，展示所有功能模块导航菜单
- **内容区域 (Content)**：主内容区，展示各模块具体内容

---

## 前端技术要求

- **响应式布局**：适配 PC（>992px）、平板（768-992px）、手机（≤768px）
- **自适应缩放**：页面随浏览器窗口缩放等比例调整
- 使用 CSS Flexbox / Grid 布局
- 使用 CSS 媒体查询实现响应式
- 导航栏在移动端可折叠（汉堡菜单）
- 侧边栏在移动端可隐藏/滑出
- 所有页面共享统一的导航栏和侧边栏组件
- **搜索表单提交**：所有筛选条件（下拉框、关键词输入）改为手动点击搜索按钮或按 Enter 键触发查询，不使用 oninput/onchange 即时触发，防止频繁 API 调用导致页面卡顿
- **密码可见性切换**：密码输入框右侧眼睛按钮，隐藏密码时显示带斜杠的眼睛图标，可见时显示普通眼睛图标

---

## 核心设计原则

1. **日志管理**：所有操作必须有日志记录（操作时间、操作类型、操作人、详情）
2. **错误处理**：前后端都需有明确的错误处理机制，前端展示友好的错误提示
3. **配置管理**：所有参数从配置文件读取，支持环境变量覆盖
4. **数据字段规范**：所有录入数据必须包含 `创建时间` 和 `到期时间` 字段
5. **到期提醒**：通过配置的邮箱自动发送到期提醒邮件；每条记录可单独设置邮件提醒开关，关闭后该条记录不参与到期提醒
6. **文件类别**：固定可选值为「合同」「专利」「车险续期」
7. **重要等级**：每条业务记录（合同/专利/车险）可设置重要等级：重要、普通、不重要（默认普通），以彩色标签展示
8. **批量操作**：合同/专利/车险页面支持全选、批量设置邮件提醒开关、批量设置重要等级
9. **可配置列显示**：合同/专利/车险页面通过"⚙️ 列显示"按钮勾选要显示的列，配置保存到 localStorage 持久化
10. **权限控制**：系统管理员拥有所有权限；业务员/财务不拥有删除权限、系统配置修改权限、用户管理权限；业务员/财务只能看到同角色用户和自己的日志

---

## API 接口 (37个)

| 模块 | 接口 | 鉴权 |
|------|------|------|
| 认证 | `POST /api/auth/login` `POST /api/auth/logout` `GET /api/auth/me` | 登出/me需登录 |
| 仪表盘 | `GET /api/dashboard/stats` `GET /api/dashboard/recent` `GET /api/dashboard/expiring` | 需登录 |
| 合同 | `GET/POST /api/contracts` `GET/PUT/DELETE /api/contracts/<id>` `PUT /api/contracts/batch` | DELETE需管理员 |
| 专利 | `GET/POST /api/patents` `GET/PUT/DELETE /api/patents/<id>` `PUT /api/patents/batch` | DELETE需管理员 |
| 车险 | `GET/POST /api/insurances` `GET/PUT/DELETE /api/insurances/<id>` `GET /api/insurances/stats` `PUT /api/insurances/batch` | DELETE需管理员 |
| 文件 | `GET /api/files` `POST /api/files/upload` `GET /api/files/<id>/download` `DELETE /api/files/<id>` | DELETE需管理员 |
| 用户 | `GET/POST /api/users` `PUT /api/users/<id>` `PUT /api/users/<id>/reset-password` `DELETE /api/users/<id>` | POST/PUT/DELETE需管理员 |
| 日志 | `GET /api/logs` `DELETE /api/logs` | 需登录 |
| 配置 | `GET/PUT /api/settings` `POST /api/settings/test-email` | PUT/POST需管理员 |
| 导出 | `POST /api/export` | 需登录 |
| 扫描 | `POST /api/scan` `POST /api/scan/import` | 需登录 |

---

## Docker 部署架构

```
用户 → http://localhost:8080
         │
    [nginx:80]  (frontend 容器)
         │
         ├── /            → 静态文件 (frontend/)
         ├── /api/*       → proxy_pass → backend:5000
         │
    [backend:5000]  (Flask 容器, python:3.11-slim)
         │
         ├── SQLite DB  → /data/suzhen.db  (bind mount 持久化)
         └── Uploads    → /data/uploads    (bind mount 持久化)
```

---

## 部署方式

### 方式一：一键安装 (setup.bat)

双击项目根目录下的 `setup.bat`，按提示操作：
1. 检测 Docker 环境（未安装则引导下载）
2. 配置国内镜像加速
3. 选择数据存储目录
4. 自动获取本机IP并启动服务

### 方式二：本地开发

```bash
# 使用 .venv 虚拟环境
.venv\Scripts\python.exe backend\run.py
# 访问: http://localhost:5000
```

### 方式三：手动 Docker

```bash
docker compose -f docker/docker-compose.yaml up -d --build
```

### 方式四：客户交付（预构建镜像）

客户无需源码，通过预构建的 Docker 镜像一键启动：

1. 安装 Docker Desktop
2. 解压 `suzhen-system-v1.0.zip`
3. 双击 `setup.bat`，输入端口 → 自动导入镜像并启动
4. 浏览器自动打开，开始使用
5. 双击 `stop.bat` 停止服务（数据通过 Docker 命名卷持久化，不丢失）

开发者构建交付包：运行 `build.bat` → 自动配置 DaoCloud 镜像加速 → 构建镜像 → 导出 tar → 打包 zip。

---

## 初始登录凭据

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin! | 管理员 |

**首次登录后请立即修改密码！**

---

## 权限分配实现

### 角色定义

| 角色 | 权限范围 |
|------|----------|
| 管理员 | 所有权限（增删改查、系统配置、用户管理、查看所有日志和用户） |
| 业务员/财务 | 增改查（无删除权限）；系统配置只读；无法访问用户管理；只能看到同角色用户和自己的日志 |

### 后端实现

| 端点 | 改动 |
|------|------|
| `DELETE /api/contracts/<id>` | `@login_required` → `@admin_required` |
| `DELETE /api/patents/<id>` | `@login_required` → `@admin_required` |
| `DELETE /api/insurances/<id>` | `@login_required` → `@admin_required` |
| `DELETE /api/files/<id>` | `@login_required` → `@admin_required` |
| `DELETE /api/logs` | `@login_required` → `@admin_required` |
| `GET /api/users` | 非管理员追加 `WHERE role = ?` 过滤同角色用户 |
| `GET /api/logs` | 非管理员追加 `WHERE user_id = ?` 过滤自己的日志 |

### 前端实现

- `app.js` 新增 `isAdmin()` 函数和 `applyPermissions()` 函数
- `applyPermissions()` 在 `DOMContentLoaded` 中自动执行，将所有 `.admin-only` 元素 `display: none`
- 各页面的删除按钮、新增/编辑/重置密码按钮、保存配置按钮、清空日志按钮均标记 `admin-only` class
- 导航栏/侧边栏中"用户管理"和"系统配置"链接标记 `admin-only` class
- `users.html`：非管理员访问时自动跳转到仪表盘
- `settings.html`：非管理员访问时所有表单字段设为 `disabled`（只读）

---

## 可配置列显示实现

合同管理、专利管理、车险续期页面支持自定义列显示：

- 表格上方提供"⚙️ 列显示"按钮，点击弹出勾选面板
- 每列通过 `data-col` 属性关联配置 key
- 默认只勾选：名称、类型、公司、业务员、到期时间、状态、备注
- 配置通过 `localStorage` 持久化（key: `contractColumns` / `patentColumns` / `insuranceColumns`）
- 隐藏列使用 CSS class `.col-hidden { display: none !important; }`
- 空数据行 `colspan` 动态计算可见列数
