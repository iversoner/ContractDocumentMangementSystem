-- ============================================================
--  素珍管理系统 - 数据库建表语句
--  使用 SQLite3，首次启动时自动执行
-- ============================================================

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    display_name TEXT NOT NULL,
    email TEXT DEFAULT '',
    role TEXT NOT NULL DEFAULT '业务员',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 合同表
CREATE TABLE IF NOT EXISTS contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    company TEXT NOT NULL,
    contact_person TEXT DEFAULT '',
    contact_phone TEXT DEFAULT '',
    contact_email TEXT DEFAULT '',
    agent TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status TEXT DEFAULT 'active',
    file_path TEXT DEFAULT '',
    remark TEXT DEFAULT '',
    source TEXT DEFAULT 'manual',
    email_reminder INTEGER DEFAULT 1,
    priority TEXT DEFAULT '普通',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 专利表
CREATE TABLE IF NOT EXISTS patents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    patent_no TEXT UNIQUE NOT NULL,
    type TEXT NOT NULL,
    holder TEXT NOT NULL,
    agent TEXT NOT NULL,
    application_date DATE NOT NULL,
    expire_date DATE NOT NULL,
    status TEXT DEFAULT 'active',
    file_path TEXT DEFAULT '',
    remark TEXT DEFAULT '',
    source TEXT DEFAULT 'manual',
    email_reminder INTEGER DEFAULT 1,
    priority TEXT DEFAULT '普通',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 车险表
CREATE TABLE IF NOT EXISTS insurances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plate_no TEXT NOT NULL,
    brand TEXT NOT NULL,
    insurance_company TEXT NOT NULL,
    insurance_type TEXT NOT NULL,
    amount REAL DEFAULT 0,
    agent TEXT NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status TEXT DEFAULT 'active',
    file_path TEXT DEFAULT '',
    remark TEXT DEFAULT '',
    source TEXT DEFAULT 'manual',
    email_reminder INTEGER DEFAULT 1,
    priority TEXT DEFAULT '普通',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 文件表
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    size INTEGER DEFAULT 0,
    uploader TEXT DEFAULT '',
    stored_path TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 操作日志表
CREATE TABLE IF NOT EXISTS operation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT DEFAULT '',
    action TEXT NOT NULL,
    module TEXT NOT NULL,
    level TEXT DEFAULT 'info',
    detail TEXT DEFAULT '',
    ip_address TEXT DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 系统配置表 (key-value)
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
