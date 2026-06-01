# 素珍管理系统 (Suzhen Management System)

## 项目概述

「素珍管理系统」—— 基于 Python 的公司综合管理系统，涵盖租赁、知识产权、合同管理、专利管理、车险续期等服务的全栈 Web 应用。使用 SQLite3 作为数据库，Docker 容器化部署。

---

## 技术栈

| 层级 | 技术选型 |
|------|----------|
| 后端 | Python 3.11+ / Flask 3.x / Gunicorn (生产) |
| 前端 | HTML5 / CSS3 / Vanilla JavaScript |
| 数据库 | SQLite3 (WAL 模式) |
| 文件存储 | 本地文件夹 (用户自选) |
| 邮件服务 | SMTP (内置于后端) |
| 部署 | Docker + Docker Compose |

---

## 初始登录凭据

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin | admin! | 管理员 |

**首次登录后请立即修改密码！**

---

## 项目文件结构

```
suzhenManagementSystem/
├── setup.bat                  # 一键安装部署脚本（给最终用户用）
├── start.bat                  # 启动脚本（多模式：全栈Docker/本地后端/混合）
├── stop.bat                   # 停止脚本
├── build.bat                  # 开发者构建打包脚本（构建镜像+导出tar+打包zip）
├── docker-compose.yaml        # 交付版 Docker Compose（使用预构建镜像）
├── CLAUDE.md                  # 本文件
├── requirement/
│   └── require.md             # 需求文档
├── frontend/                  # 前端静态页面
│   ├── index.html             # 入口页面（登录页）
│   ├── css/
│   │   └── style.css          # 全局样式（响应式）
│   ├── js/
│   │   └── app.js             # 全局 JS（API 请求、导航、登录等）
│   └── pages/
│       ├── login.html         # 登录页面
│       ├── dashboard.html     # 仪表盘
│       ├── contract.html      # 合同管理
│       ├── patent.html        # 专利管理
│       ├── insurance.html     # 车险续期管理
│       ├── files.html         # 文件管理
│       ├── users.html         # 用户管理
│       ├── settings.html      # 系统配置
│       ├── logs.html          # 系统日志
│       └── export.html        # 数据导出
├── backend/                   # 后端代码
│   ├── run.py                 # 启动入口 (支持 python run.py / gunicorn run:app)
│   ├── app.py                 # Flask 工厂函数 (环境变量覆盖配置)
│   ├── config.yaml            # 全局配置
│   ├── requirements.txt       # Python 依赖
│   ├── database/
│   │   ├── db.py              # SQLite3 连接管理
│   │   └── schema.sql         # 7 张表建表语句
│   ├── models/
│   ├── routes/                # 11 个蓝图 (37个API接口)
│   │   ├── auth.py            # 认证
│   │   ├── dashboard.py       # 仪表盘
│   │   ├── contract.py        # 合同 CRUD
│   │   ├── patent.py          # 专利 CRUD
│   │   ├── insurance.py       # 车险 CRUD + 统计
│   │   ├── file.py            # 文件上传下载
│   │   ├── user.py            # 用户管理
│   │   ├── log.py             # 系统日志
│   │   ├── setting.py         # 系统配置
│   │   ├── export.py          # 数据导出
│   │   └── scan.py            # 目录扫描 & 批量导入
│   ├── services/
│   │   ├── auth_service.py    # bcrypt 密码哈希 + JWT
│   │   ├── email_service.py   # SMTP 邮件发送
│   │   └── log_service.py     # 统一日志写入
│   ├── middleware/
│   │   ├── auth_middleware.py  # login_required / admin_required 装饰器
│   │   └── error_handler.py   # 全局异常处理
│   └── uploads/               # 文件上传目录
├── build/                    # 客户交付包
│   ├── setup.bat             #   客户一键启动
│   ├── stop.bat              #   客户停止服务
│   ├── docker-compose.yaml   #   交付版编排
│   ├── nginx.conf            #   nginx 配置
│   └── suzhen-images.tar     #   预构建镜像（build.bat 生成）
└── docker/                    # Docker 配置
    ├── Dockerfile              # 前端镜像 (nginx:alpine)
    ├── Dockerfile.backend      # 后端镜像 (python:3.11-slim + gunicorn)
    ├── nginx.conf              # nginx 配置 (静态文件 + /api 反向代理)
    ├── docker-compose.yaml     # 全栈编排 (frontend + backend + 网络)
    ├── .dockerignore           # 排除 .venv / __pycache__ 等
    └── .env                    # 由 setup.bat 生成 (DATA_DIR, APP_PORT)
```

---

## Docker 部署架构

```
用户 → http://localhost:8080
         │
    [nginx:80]  (frontend 容器, nginx:alpine)
         │
         ├── /            → 静态文件 (frontend/)
         ├── /api/*       → proxy_pass → backend:5000
         │
    [backend:5000]  (Flask 容器, python:3.11-slim + gunicorn)
         │
         ├── SQLite DB  → /data/suzhen.db  (bind mount → 用户选择的本地目录)
         └── Uploads    → /data/uploads    (bind mount → 用户选择的本地目录)
```

### 关键设计点

- **nginx 反向代理 /api**：前端通过相对路径 `/api` 访问后端，无需 CORS
- **bind mount 持久化**：用户选择本地目录映射到容器 `/data`，数据不随容器销毁而丢失
- **环境变量覆盖**：app.py 所有配置项都支持环境变量覆盖，Docker 内通过 compose environment 传入
- **pip 镜像加速**：Dockerfile.backend 内置阿里云 pip 镜像源
- **docker-compose .env**：setup.bat 生成 `.env` 文件，配置 DATA_DIR 和 APP_PORT

---

## 部署方式

### 方式一：一键安装（推荐给最终用户）

双击项目根目录下的 **`setup.bat`**，按提示完成 5 个步骤：

| 步骤 | 说明 |
|------|------|
| 1. 检测 Docker | 自动检测 Docker Desktop 是否安装，未安装则引导下载 |
| 2. 配置镜像 | 可选阿里云/1ms.run 镜像加速（国内必须） |
| 3. 选择数据目录 | 选择本地目录存储数据库和上传文件 |
| 4. 获取 IP | 自动读取本机 IPv4，用户配置端口 |
| 5. 构建启动 | 拉取镜像、构建服务、启动全栈 |

启动后自动打开浏览器访问系统。

### 方式二：手动 Docker

```bash
# 停止旧容器
docker compose -f docker/docker-compose.yaml down

# 构建并启动
docker compose -f docker/docker-compose.yaml up -d --build

# 查看日志
docker compose -f docker/docker-compose.yaml logs -f

# 停止
docker compose -f docker/docker-compose.yaml down
```

### 方式三：本地开发

```bash
# 使用 .venv 虚拟环境
.venv\Scripts\python.exe backend\run.py
# 访问: http://localhost:5000/api
```

---

## API 接口 (37个)

| 模块 | 接口 | 鉴权 |
|------|------|------|
| 认证 | `POST /api/auth/login` `POST /api/auth/logout` `GET /api/auth/me` | 登出/me需登录 |
| 仪表盘 | `GET /api/dashboard/stats` `GET /api/dashboard/recent` `GET /api/dashboard/expiring` | 需登录 |
| 合同 | `GET/POST /api/contracts` `GET/PUT/DELETE /api/contracts/<id>` `PUT /api/contracts/batch` | 需登录 |
| 专利 | `GET/POST /api/patents` `GET/PUT/DELETE /api/patents/<id>` `PUT /api/patents/batch` | 需登录 |
| 车险 | `GET/POST /api/insurances` `GET/PUT/DELETE /api/insurances/<id>` `GET /api/insurances/stats` `PUT /api/insurances/batch` | 需登录 |
| 文件 | `GET /api/files` `POST /api/files/upload` `GET /api/files/<id>/download` `DELETE /api/files/<id>` | 需登录 |
| 用户 | `GET/POST /api/users` `PUT /api/users/<id>` `PUT /api/users/<id>/reset-password` `DELETE /api/users/<id>` | POST/PUT/DELETE需管理员 |
| 日志 | `GET /api/logs` `DELETE /api/logs` | 需登录 |
| 配置 | `GET/PUT /api/settings` `POST /api/settings/test-email` | PUT/POST需管理员 |
| 导出 | `POST /api/export` (type: all/byCreate/byExpire, format: json/csv) | 需登录 |
| 扫描 | `POST /api/scan` `POST /api/scan/import` | 需登录 |

### 快速验证

```bash
# 登录获取 token
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin!"}'

# 用返回的 token 访问合同列表
curl http://localhost:5000/api/contracts \
  -H "Authorization: Bearer <token>"
```

---

## 配置说明

### config.yaml 主要配置项

```yaml
app:
  secret_key: suzhen-secret-key-change-in-production
  debug: true

server:
  host: 0.0.0.0
  port: 5000

database:
  path: backend/database/suzhen.db

admin:
  username: admin
  password: admin!           # 初始管理员密码

email:                       # SMTP 邮件配置
  smtp_server: smtp.example.com
  smtp_port: 587

storage:
  upload_folder: backend/uploads
  max_file_size: 10485760    # 10 MB

reminder:
  enabled: false
  days_before: 30
```

所有配置项都支持通过**同名环境变量**覆盖（app.py 中实现），Docker 部署时通过 compose environment 传入。

---

## 数据库表 (7张)

| 表名 | 说明 |
|------|------|
| users | 用户表 |
| contracts | 合同表 |
| patents | 专利表 |
| insurances | 车险续期表 |
| files | 文件表 |
| operation_logs | 操作日志表 |
| settings | 系统配置表 (key-value) |

---

## 当前任务状态

- [x] 第一步：基础前端静态页面
- [x] 第二步：后端 API 开发
- [x] 第三步：前后端联调
- [x] 第四步：全栈 Docker 容器化
- [x] 一键安装脚本 setup.bat
- [x] 需求文档整理
- [x] 邮件提醒列 + 重要等级 + 批量操作
- [x] 所有页面搜索改为手动按钮提交
- [x] 密码眼睛图标修复
- [x] 可配置列显示（合同/专利/车险页面）
- [x] 权限分配（管理员全部权限 / 业务员无删除、无系统配置、无用户管理、同角色可见、自己日志可见）
- [x] 交付打包（预构建 Docker 镜像 + 客户一键启动脚本 + DaoCloud 镜像加速）

---

## 各页面功能详情

| 页面 | 文件 | 功能 |
|------|------|------|
| 登录页 | `index.html` / `login.html` | 用户名/密码登录，对接后端 JWT 认证 |
| 仪表盘 | `dashboard.html` | 8个统计卡片、到期提醒横幅、最近项目列表、即将到期列表（仅显示邮件提醒开启的项目） |
| 合同管理 | `contract.html` | 表格展示全部字段、类别/状态/关键词筛选(手动搜索按钮)、增删改查、详情弹窗、分页、邮件提醒开关列、重要等级标签列、全选/批量设置邮件提醒/批量设置等级 |
| 专利管理 | `patent.html` | 表格展示全部字段、类型/状态/关键词筛选(手动搜索按钮)、增删改查、详情弹窗、分页、邮件提醒开关列、重要等级标签列、全选/批量设置邮件提醒/批量设置等级 |
| 车险续期 | `insurance.html` | 页面级统计卡片、状态/保险公司/关键词筛选(手动搜索按钮)、增删改查、详情弹窗、分页、邮件提醒开关列、重要等级标签列、全选/批量设置邮件提醒/批量设置等级 |
| 文件管理 | `files.html` | 文件上传/下载/删除、类别固定可选(合同/专利/车险续期)、类别/关键词筛选(手动搜索按钮)、分页 |
| 用户管理 | `users.html` | 用户增删改查、角色/状态筛选(手动搜索按钮)、重置密码（管理员专用） |
| 系统配置 | `settings.html` | 邮箱SMTP配置、数据库配置、到期提醒配置、文件存储配置、测试发送、密码眼睛图标(隐藏=斜杠眼/可见=普通眼) |
| 系统日志 | `logs.html` | 级别/模块筛选(手动搜索按钮)、关键词搜索、清空日志、分页 |
| 数据导出 | `export.html` | 三种导出方式(全部/按创建时间/按到期时间)、日期范围选择、JSON/CSV |

### 全局技术特性

- **响应式布局**：CSS 变量体系 + 媒体查询三档适配 (PC >992px / 平板 768-992px / 手机 ≤768px)
- **移动端适配**：汉堡菜单、侧边栏滑出、遮罩层、表格横向滚动
- **统一布局**：顶部导航栏 + 左侧侧边栏 + 主内容区
- **API_BASE 自适应**：Docker 部署用 `/api`（相对路径），本地开发用 `http://localhost:5000/api`
- **交互反馈**：Toast 消息、模态框表单、confirm 确认对话框
- **搜索表单提交**：所有页面筛选/搜索改为手动点击搜索按钮或 Enter 键触发，避免 oninput/onchange 频繁 API 调用
- **密码可见性切换**：隐藏密码时显示带 CSS 斜杠的眼睛图标，可见时显示普通眼睛图标

---

## 邮件提醒 & 重要等级功能实现

### 数据库
- contracts、patents、insurances 三张表新增 `email_reminder` (INTEGER DEFAULT 1) 和 `priority` (TEXT DEFAULT '普通') 两列
- 兼容迁移：`db.py` 的 `init_db()` 中通过 `PRAGMA table_info` 检查列是否存在，不存在则 `ALTER TABLE ADD COLUMN`

### 后端
- 三个 CRUD 路由的 `_row_to_dict` 增加 `emailReminder` (bool) 和 `priority` (str) 字段
- INSERT/UPDATE 操作包含两个新字段
- 新增 `PUT /contracts/batch`、`PUT /patents/batch`、`PUT /insurances/batch` 批量更新接口，支持 `{ids: [int], field: 'email_reminder'|'priority', value: any}`
- dashboard 的 `expiring` 接口 SQL 增加 `AND email_reminder = 1` 过滤，只返回需要提醒的记录

### 前端
- 合同/专利/车险页面表格增加"邮件提醒"复选框列和"重要等级"彩色标签列
- 表头全选复选框 + 批量操作栏（开启/关闭邮件提醒、设置重要等级）
- 新增/编辑模态框包含邮件提醒复选框（默认勾选）和重要等级下拉（默认普通）
- 共享工具函数：`toggleSelectAll()`、`updateBatchBar()`、`getCheckedIds()`、`toggleReminder()`、`batchUpdate()`、`getPriorityBadge()`

---

## 可配置列显示

合同/专利/车险页面支持用户自定义表格列显示：

### 实现方式
- 表格上方提供"⚙️ 列显示"按钮，点击弹出勾选面板（`column-toggle-panel`）
- 所有 `<th>` 和 `<td>` 通过 `data-col` 属性关联配置 key
- 每页定义 `COLUMN_CONFIG` 数组（key / label 映射）
- 默认只勾选：名称、类型、公司、业务员、到期时间、状态、备注
- 配置通过 `localStorage` 持久化（key: `contractColumns` / `patentColumns` / `insuranceColumns`）
- 隐藏列使用 CSS class `.col-hidden { display: none !important; }`
- 空数据行的 `colspan` 动态计算可见列数（`getVisibleCount()`）

### 涉及文件
- `frontend/css/style.css` — `.col-hidden`、`.column-toggle-panel` 样式
- `frontend/pages/contract.html` — 12 列可配置
- `frontend/pages/patent.html` — 12 列可配置（含专利号）
- `frontend/pages/insurance.html` — 14 列可配置（含车牌号、品牌、保险公司、险种、金额）

---

## 权限分配

### 角色权限矩阵

| 操作 | 管理员 | 业务员/财务 |
|------|--------|-------------|
| 增/改/查 | Yes | Yes |
| 删除（合同/专利/车险/文件） | Yes | No (前端隐藏 + 后端 403) |
| 用户管理 | Yes | No (页面跳转 + 后端 403) |
| 系统配置修改 | Yes | No (只读 + 后端 403) |
| 用户列表 | 所有用户 | 仅同角色用户 |
| 日志列表 | 所有日志 | 仅自己的日志 |
| 清空日志 | Yes | No (前端隐藏 + 后端 403) |

### 后端实现
- 5 个 DELETE 端点从 `@login_required` 改为 `@admin_required`：
  `contract.py`、`patent.py`、`insurance.py`、`file.py`、`log.py`
- `user.py` GET /users：非管理员追加 `WHERE role = ?` 过滤
- `log.py` GET /logs：非管理员追加 `WHERE user_id = ?` 过滤
- `setting.py` PUT /settings 和 POST /test-email 已使用 `@admin_required`

### 前端实现
- `app.js` 新增 `isAdmin()` 和 `applyPermissions()` 函数
- `applyPermissions()` 在 `DOMContentLoaded` 中执行，隐藏所有 `.admin-only` 元素
- 各页面导航栏/侧边栏中"用户管理"和"系统配置"链接标记 `admin-only` class
- 所有删除按钮、新增/编辑/重置密码按钮、保存配置按钮、清空日志按钮标记 `admin-only`
- `users.html`：非管理员访问时 `DOMContentLoaded` 中跳转到 dashboard.html
- `settings.html`：非管理员访问时所有表单字段 `disabled`

---

## 交付打包（预构建 Docker 镜像分发）

客户无需源码，通过预构建的 Docker 镜像运行系统。

### 交付包结构

```
suzhen-system-v1.0.zip
├── setup.bat              # 客户一键启动脚本
├── stop.bat               # 停止服务脚本
├── suzhen-images.tar      # 预构建 Docker 镜像（backend + frontend）
├── docker-compose.yaml    # 交付版编排配置（使用 image，Docker 命名卷）
└── nginx.conf             # nginx 配置（外部挂载，不在镜像内）
```

### 开发者构建流程

1. 运行 `build.bat`（根目录）
2. 自动配置 DaoCloud 镜像加速（`https://www.daocloud.io/mirror`）
3. 构建 docker/docker-compose.yaml 中的镜像（从源码 build）
4. `docker save` 导出镜像为 `build/suzhen-images.tar`
5. 打包 `build/` 目录为 `suzhen-system-v1.0.zip`

### 客户操作流程

1. 安装 Docker Desktop（需重启电脑）
2. 解压 zip 到任意目录
3. 双击 `setup.bat` → 输入端口 → 自动 `docker load` 导入镜像并启动
4. 浏览器访问 `http://localhost:端口`
5. 双击 `stop.bat` 停止服务（数据通过 Docker 命名卷 `suzhen-data` 持久化）

### 关键文件说明

| 文件 | 用途 |
|------|------|
| `build.bat` | 开发者用 — 配置镜像加速 + 构建镜像 + 导出 tar + 打包 zip |
| `build/setup.bat` | 客户用 — 检测 Docker → 导入镜像 → 输端口 → 启动 |
| `build/stop.bat` | 客户用 — `docker compose down` |
| `build/docker-compose.yaml` | 交付版 — 使用 `image:` + Docker 命名卷，无需 build |
| `docker/docker-compose.yaml` | 开发版 — 使用 `build:` 从源码构建 |
| `build/nginx.conf` | nginx 配置（从 `docker/nginx.conf` 复制），交付版 compose bind mount 引用 |

### 数据持久化

交付版使用 Docker 命名卷 `suzhen-data` 存储数据库和上传文件，对客户透明：
- 容器删除后数据不丢失
- 客户无需选择目录
- 如需彻底清理：`docker volume rm suzhen-data`

### 源码安全

- Python 源码在 Docker 镜像内部（`/app`），客户无法直接访问
- 交付包中不包含任何 `.py`、`.html`、`.js` 源码文件
- 如需进一步加固，后续可考虑 Cython 编译或 PyArmor 混淆
