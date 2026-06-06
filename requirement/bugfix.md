# Bug Fix Log

## 2026-06-03

### Fix 1: Logout Redirects to 404

**Symptom**: After clicking logout, user lands on a 404 page instead of the login page.

**Root Cause**: `frontend/js/app.js` had three instances of `window.location.href = '../login.html'`. When the user is on `/pages/dashboard.html`, `../login.html` resolves to `/login.html`, which does not exist. The actual login page is `/index.html`.

**Affected Locations**:
- `handleLogout()` — line 300
- 401 error handler in `API.request()` — line 74
- `requireLogin()` — line 310

**Fix**: Changed all three to `window.location.href = '../index.html'`.

**Files Changed**:
- `frontend/js/app.js`

---

### Fix 2: Multi-User Session Analysis ("One User Logs Out, All Lose Session")

**Symptom**: User reported that when one person logs out, all other users on different devices get forcibly logged out.

**Investigation Result**: This is NOT a direct code bug — JWT authentication is purely stateless. One user's logout only clears their own localStorage and writes a log entry. It does not invalidate other users' tokens.

**Actual Cause**: The symptom is caused by simultaneous JWT token expiration (all tokens expire after 24 hours). When all users' tokens expire at the same time, each user gets a 401 response. The 401 handler then redirects to the broken `../login.html` path (see Fix 1), resulting in a 404. Users perceive this as "everyone got logged out at once".

**Mitigation**: Fix 1 resolves the immediate UX issue. For production use, consider implementing a token blacklist table and a `user_disabled` status check in the auth middleware for forced logout capability.

**Files Changed**: None (analysis only; mitigation via Fix 1)

---

### Fix 3: File Download Shows Toast Only (No Actual Download)

**Symptom**: Clicking the download button on the file management page only shows a toast message "正在下载 xxx (模拟)" (Downloading xxx (simulated)), but no actual file download occurs.

**Root Cause**: `frontend/pages/files.html` line 139 — the per-file download button was a stub:
```html
onclick="showToast('正在下载 ${f.name} (模拟)', 'info')"
```
It never called the actual download API. The backend `/files/<id>/download` endpoint and `API.download()` method were both fully implemented and working.

**Fix**: Replaced the stub with an actual `API.download()` call:
```html
onclick="API.download('/files/${f.id}/download', '${f.name.replace(/'/g, "\\'")}')"
```

**Files Changed**:
- `frontend/pages/files.html`

---

### Fix 4: Add Favicon to All Pages

**Symptom**: All pages had the default browser tab icon. No custom favicon.

**Fix**: Created `frontend/favicon.svg` — a blue rounded square with white "S" letter, matching the system's blue-and-white color scheme. Added `<link rel="icon" href="...">` to all 11 HTML files.

**Files Changed**:
- `frontend/favicon.svg` (new)
- `frontend/index.html`
- `frontend/pages/login.html`
- `frontend/pages/dashboard.html`
- `frontend/pages/contract.html`
- `frontend/pages/patent.html`
- `frontend/pages/insurance.html`
- `frontend/pages/files.html`
- `frontend/pages/users.html`
- `frontend/pages/settings.html`
- `frontend/pages/logs.html`
- `frontend/pages/export.html`

---

### Fix 5: Remove Chinese Characters from Configuration Files

**Symptom**: Chinese characters in `.bat`, `.yaml`, `.env`, and `nginx.conf` files cause encoding issues on some Windows systems, potentially breaking Docker Compose or Nginx startup.

**Affected Files**:
- `backend/config.yaml` — Chinese comments and runtime values (`name`, `display_name`, `sender_name`)
- `build/docker-compose.yaml` — Chinese comments
- `build/nginx.conf` — Chinese comments

**Fix**: Replaced all Chinese text with English equivalents. Verified all 17 config files (bat, yaml, env, nginx.conf, Dockerfile) contain zero Chinese characters.

**Files Changed**:
- `backend/config.yaml`
- `build/docker-compose.yaml`
- `build/nginx.conf`

---

### Fix 6: File Scanning — Sub-directory Browsing, File Selection, and Windows Path Translation

**Symptom**: The file scanning feature had three issues:
1. All files were imported at once — no individual file selection (all-or-nothing)
2. `os.walk` recursively flattened all subdirectories — no way to browse by folder
3. Windows host paths (e.g., `D:\contract`) were unrecognized inside Docker containers

**Fix**: Complete rewrite of the scan feature:

**Backend** (`backend/routes/scan.py`):
- Added `_translate_path()` — translates Windows paths to Linux container paths using the configured `HOST_DATA_DIR`. Paths not under the allowed directory are rejected with `errorType: 'invalid_path'`.
- Replaced `_scan_dir()` (recursive `os.walk`) with `_scan_dir_nonrecursive()` (single-level `os.listdir`) that returns `{files, subdirs, currentDir, parentDir}`.
- Rewrote `POST /api/scan` to use path translation and non-recursive scan, returning subdirectory lists and breadcrumb navigation data.

**Backend Config**:
- `backend/config.yaml` — added `host_data_dir` config entry
- `backend/app.py` — reads `HOST_DATA_DIR` environment variable

**Frontend** (`frontend/js/app.js`):
- Added `ScanHelper` shared object with: `init()`, `openModal()`, `scanDirectory()`, `navigateToSubdir()`, `navigateUp()`, `importFiles()`, checkbox management, and breadcrumb navigation.
- Extracted duplicated scan logic from 3 pages into a single shared module.

**Frontend Pages** (contract.html, patent.html, insurance.html):
- Redesigned sync modal: scan button inline with input, result area with border, "Import Selected" button
- Results show: breadcrumb navigation, "Back to parent" button, subdirectory buttons, file table with checkboxes (select all + individual), collapsible "already exists" section
- Removed old inline scan JS, delegated to `ScanHelper`

**Docker**:
- `docker/docker-compose.yaml` — added `HOST_DATA_DIR` env var
- `docker/.env` — added `HOST_DATA_DIR` entry
- `build/docker-compose.yaml` — changed from named volume to bind mount, added `HOST_DATA_DIR`
- `setup.bat` — writes `HOST_DATA_DIR` to `.env`
- `build/setup.bat` — added data directory selection step, writes `DATA_DIR` and `HOST_DATA_DIR` to `.env`

**Files Changed**:
- `backend/config.yaml`
- `backend/app.py`
- `backend/routes/scan.py`
- `frontend/js/app.js`
- `frontend/css/style.css`
- `frontend/pages/contract.html`
- `frontend/pages/patent.html`
- `frontend/pages/insurance.html`
- `docker/docker-compose.yaml`
- `docker/.env`
- `setup.bat`
- `build/docker-compose.yaml`
- `build/setup.bat`

---

### Fix 7: Auto Email Reminder Never Fires (Missing Scheduler)

**Symptom**: Manual test email works (via Settings page "Test Send" button), but automatic scheduled reminders never arrive, even when `reminder_enabled=true` and `reminder_send_time` is set.

**Root Cause**: `send_reminder_email()` in `backend/services/email_service.py` is fully implemented and correct, but **no code anywhere invokes it**. The project had zero scheduling infrastructure — no APScheduler, no background thread, no cron job. The function was dead code.

**Fix**:
- Created `backend/services/scheduler_service.py`:
  - Uses `APScheduler` `BackgroundScheduler` with `timezone='Asia/Shanghai'`
  - Checks every 60 seconds: reads `reminder_enabled`, `reminder_send_time`, `reminder_days_before` from `settings` table
  - When Beijing time matches `send_time` (minute precision), queries contracts/patents/insurances tables for items expiring within `days_before` days (`status='active'` AND `email_reminder=1`)
  - Calls `send_reminder_email()` with collected items
  - Once-per-day guard (`_last_sent_date`) prevents duplicate sends
  - Standalone SQLite connection (not Flask `g`-based) for background thread safety
  - Atomic file lock (`os.O_CREAT | os.O_EXCL`) prevents duplicate schedulers across gunicorn's 4 workers
- Updated `backend/run.py` to call `init_scheduler(app)` on startup and `atexit.register(shutdown_scheduler)`
- Added `APScheduler>=3.10,<4.0` to `backend/requirements.txt`

**Files Changed**:
- `backend/services/scheduler_service.py` (new)
- `backend/run.py`
- `backend/requirements.txt`

---

### Fix 8: .bat Files — Delivery Package and Step Numbering

**Symptom 1**: `build.bat` used `Compress-Archive -Path 'build\*'` which would include a stale `build/.env` if it existed from a prior run.

**Symptom 2**: `build/setup.bat` still showed "Step 1/3, 2/3, 3/3" after adding the data directory selection step (Step 2.5/3).

**Fix**:
- `build.bat`: Changed to explicitly list the 5 delivery files instead of `build\*` wildcard
- `build/setup.bat`: Renumbered all steps from 3 to 4 (1/4 Check Docker, 2/4 Import Images, 3/4 Select Data Directory, 4/4 Start Services)

**Files Changed**:
- `build.bat`
- `build/setup.bat`

---

### Fix 9: Missing GET /api/users/<id> Endpoint (User Edit Broken)

**Symptom**: Clicking "Edit" on a user in the user management page shows "获取用户失败" (Failed to get user) error. The edit modal cannot populate user data.

**Root Cause**: `frontend/pages/users.html` `editUser()` function calls `API.get('/users/' + id)`, but `backend/routes/user.py` only had `GET /users` (list) and no `GET /users/<id>` (detail) endpoint.

**Fix**: Added `GET /api/users/<id>` endpoint with permission check (non-admin users can only view same-role users).

**Files Changed**:
- `backend/routes/user.py`

---

### Fix 10: Missing File Upload Input Element (Upload Button Broken)

**Symptom**: Clicking the "Upload File" button on the file management page does nothing.

**Root Cause**: `frontend/pages/files.html` line 77 calls `document.getElementById('fileUploadInput').click()`, but there was no `<input type="file" id="fileUploadInput">` element anywhere in the page. The `handleFileUpload()` function was orphaned — defined but never wired to any DOM element.

**Fix**: Added `<input type="file" id="fileUploadInput" style="display:none" onchange="handleFileUpload(this)" multiple>` inside the `<main>` section.

**Files Changed**:
- `frontend/pages/files.html`

---

### Fix 11: Missing SECRET_KEY in Dev Docker Compose

**Symptom**: JWT tokens generated in the development Docker environment use the default config.yaml secret key, which is insecure and causes issues if config.yaml is not mounted.

**Root Cause**: `docker/docker-compose.yaml` backend environment section was missing `SECRET_KEY`, unlike `build/docker-compose.yaml` which has it.

**Fix**: Added `SECRET_KEY=${SECRET_KEY:-suzhen-secret-key-change-in-production}` to dev docker-compose backend environment.

**Files Changed**:
- `docker/docker-compose.yaml`

---

### Fix 12: Source Column Not Displayed in Frontend

**Symptom**: Backend returns `source` field (values: `'manual'` or `'scan'`) for contracts, patents, and insurances, but it was never displayed in the frontend tables.

**Fix**: Added "来源" (Source) column to contract, patent, and insurance table headers, row templates, and COLUMN_CONFIG arrays. Shows "扫描导入" (Scan Import) with blue badge for `scan` records, "手动录入" (Manual Entry) with gray badge for `manual` records. Added `.badge.info` and `.badge.default` CSS classes.

**Files Changed**:
- `frontend/pages/contract.html`
- `frontend/pages/patent.html`
- `frontend/pages/insurance.html`
- `frontend/css/style.css`

---

### Fix 13: UpdatedAt Column Not Displayed in Frontend

**Symptom**: Backend returns `updatedAt` field for contracts, patents, and insurances, but it was never displayed in the frontend tables.

**Fix**: Added "更新时间" (Updated At) column to contract, patent, and insurance table headers, row templates, and COLUMN_CONFIG arrays.

**Files Changed**:
- `frontend/pages/contract.html`
- `frontend/pages/patent.html`
- `frontend/pages/insurance.html`

---

### Fix 14: Hardcoded Python Version in Dockerfile Breaks Cross-Machine Build

**Symptom**: `docker compose up -d --build` fails on a different computer with `docker.io/library/python:3.11-slim: not found`. Also, compose `version` attribute is obsolete and produces warnings.

**Root Cause**: 
1. `docker/Dockerfile.backend` had `FROM python:3.11-slim` hardcoded — if Docker Hub can't resolve that specific tag on a different machine (network/mirror issues), build fails.
2. `docker/docker-compose.yaml` and `build/docker-compose.yaml` had `version: "3.9"` which Docker Compose v2+ ignores and warns about.

**Fix**: 
- Changed `FROM python:3.11-slim` to `ARG PYTHON_VERSION=3.11` + `FROM python:${PYTHON_VERSION}-slim`, allowing override via `PYTHON_VERSION` build arg
- Added `args: - PYTHON_VERSION=${PYTHON_VERSION:-3.11}` in compose backend build section
- Removed `version: "3.9"` from both compose files

**Files Changed**:
- `docker/Dockerfile.backend`
- `docker/docker-compose.yaml`
- `build/docker-compose.yaml`
- `CLAUDE.md` (updated description)

---

### Fix 15: Scan Blueprint Missing url_prefix — Backend Crash on Startup

**Symptom**: Backend fails to start with `ValueError: URL rule '' must start with a slash.`

**Root Cause**: `backend/routes/__init__.py` registered `scan_bp` without a `url_prefix`, while the scan routes defined `''` and `/api/scan/import` as route paths. Flask requires all routes to start with `/`, so the empty string route caused a startup crash.

**Fix**:
- Added `url_prefix='/api/scan'` to scan blueprint registration in `__init__.py`
- Fixed `/api/scan/import` route to `/import` (removed redundant prefix)
- Fixed `/api/scan/import-dirs` route to `/import-dirs` (removed redundant prefix)

**Files Changed**:
- `backend/routes/__init__.py`
- `backend/routes/scan.py`

---

### Fix 16: Old bulk_import Missing file_name Field

**Symptom**: The old `POST /api/scan/import` endpoint (single-level file import) did not save `file_name` to the database, only `file_path`. Records imported via this route would have empty `file_name`.

**Root Cause**: The INSERT statements in `bulk_import()` were never updated when the `file_name` column was added to the schema.

**Fix**: Added `file_name` to all three INSERT statements in `bulk_import()` (contract/patent/insurance).

**Files Changed**:
- `backend/routes/scan.py`

---

### Fix 17: Scan Dedup Only Matched file_path (Not file_name)

**Symptom**: If a file was moved to a different directory (e.g., `/data/合同/合同.pdf` → `/data/归档/合同.pdf`), the scan feature would treat it as a new file and create a duplicate record. The `file_path` changed but the `file_name` (原始文件名) stayed the same.

**Root Cause**: Both `scan_directory()` and `import_directories()` only used `file_path` for deduplication. The `file_name` field was stored but never used for matching.

**Fix**: 
- `scan_directory()`: Query both `file_path` and `file_name` from DB; a file is considered "existing" if either `file_path` OR `file_name` matches
- `import_directories()`: Same dual-set matching; after import, both `file_path` and `file_name` are added to their respective sets to prevent intra-batch duplicates
- `bulk_import()`: SQL WHERE changed from `file_path = ?` to `file_path = ? OR (file_name != '' AND file_name = ?)`

**Files Changed**:
- `backend/routes/scan.py`
