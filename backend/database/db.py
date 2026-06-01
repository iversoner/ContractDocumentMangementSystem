"""
数据库连接管理
使用 Flask g 对象在每个请求周期内复用连接
"""
import sqlite3
import os
from datetime import datetime, timezone, timedelta

from flask import g, current_app


def beijing_now():
    """返回北京时间字符串 (UTC+8)"""
    return datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')


def utc_to_beijing(utc_str):
    """将 UTC 时间字符串转为北京时间字符串"""
    if not utc_str:
        return utc_str
    try:
        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d']:
            try:
                dt = datetime.strptime(utc_str, fmt)
                dt = dt.replace(tzinfo=timezone.utc) + timedelta(hours=8)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                continue
        return utc_str
    except Exception:
        return utc_str


def get_db_path():
    """获取数据库文件绝对路径"""
    rel_path = current_app.config.get('DATABASE_PATH', 'backend/database/suzhen.db')
    if not os.path.isabs(rel_path):
        rel_path = os.path.join(current_app.root_path, '..', rel_path)
    return os.path.normpath(rel_path)


def get_db():
    """获取当前请求的数据库连接"""
    if 'db' not in g:
        db_path = get_db_path()
        # 确保目录存在
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        g.db = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys=ON")
        # 注册北京时间 SQLite 函数
        g.db.create_function('beijing_now', 0, beijing_now)
    return g.db


def close_db(e=None):
    """关闭数据库连接"""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """执行建表 SQL 并创建默认管理员，同时处理schema迁移"""
    db = get_db()
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    with open(schema_path, 'r', encoding='utf-8') as f:
        db.executescript(f.read())
    db.commit()

    # ---- Schema 迁移：为旧表补充 source 字段 ----
    migrations = [
        ("contracts", "source", "TEXT DEFAULT 'manual'"),
        ("patents", "source", "TEXT DEFAULT 'manual'"),
        ("insurances", "source", "TEXT DEFAULT 'manual'"),
    ]
    for table, col, col_def in migrations:
        existing = db.execute(f"PRAGMA table_info({table})").fetchall()
        col_names = [r[1] for r in existing]
        if col not in col_names:
            db.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")
    db.commit()

    # ---- Schema 迁移：为旧表补充 email_reminder + priority 字段 ----
    new_migrations = [
        ("contracts", "email_reminder", "INTEGER DEFAULT 1"),
        ("contracts", "priority", "TEXT DEFAULT '普通'"),
        ("patents", "email_reminder", "INTEGER DEFAULT 1"),
        ("patents", "priority", "TEXT DEFAULT '普通'"),
        ("insurances", "email_reminder", "INTEGER DEFAULT 1"),
        ("insurances", "priority", "TEXT DEFAULT '普通'"),
    ]
    for table, col, col_def in new_migrations:
        existing = db.execute(f"PRAGMA table_info({table})").fetchall()
        col_names = [r[1] for r in existing]
        if col not in col_names:
            db.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")
    db.commit()

    # 创建默认管理员（如不存在）
    admin_config = current_app.config.get('ADMIN_CONFIG', {})
    username = admin_config.get('username', 'admin')
    existing = db.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
    if not existing:
        from services.auth_service import hash_password
        password_hash = hash_password(admin_config.get('password', 'admin123'))
        db.execute(
            "INSERT INTO users (username, password_hash, display_name, email, role, status) VALUES (?, ?, ?, ?, ?, ?)",
            (username, password_hash,
             admin_config.get('display_name', '管理员'),
             admin_config.get('email', ''),
             '管理员', 'active')
        )
        db.commit()


def init_app(app):
    """在 Flask 应用中注册数据库模块"""
    app.teardown_appcontext(close_db)
    with app.app_context():
        init_db()
