"""
Background scheduler for automatic email reminders.
Uses APScheduler to periodically check and send expiry reminder emails.
"""
import os
import sys
import time
import sqlite3
import logging
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)

_scheduler = None


def _beijing_now():
    return datetime.now(timezone(timedelta(hours=8)))


def _get_db_connection(app):
    """Open a standalone database connection (not Flask g-based, safe for background threads)."""
    db_path = app.config.get('DATABASE_PATH', 'backend/database/suzhen.db')
    if not os.path.isabs(db_path):
        db_path = os.path.join(app.root_path, '..', db_path)
    db_path = os.path.normpath(db_path)
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _write_system_log(db, action, module, level='info', detail=''):
    """Write to operation_logs using a standalone connection."""
    now = _beijing_now().strftime('%Y-%m-%d %H:%M:%S')
    db.execute(
        "INSERT INTO operation_logs (user_id, username, action, module, level, detail, ip_address, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (None, 'system', action, module, level, detail, '', now)
    )
    db.commit()


def _check_and_send_reminders(app):
    """Check reminder settings and send expiry reminder emails."""
    db = None
    try:
        db = _get_db_connection(app)
        now = _beijing_now()
        current_time = now.strftime('%H:%M')
        today = now.strftime('%Y-%m-%d')

        # Step 1: check enabled
        row = db.execute("SELECT value FROM settings WHERE key='reminder_enabled'").fetchone()
        enabled_db = row['value'] if row else None
        enabled = (enabled_db.lower() == 'true') if enabled_db is not None else bool(app.config.get('REMINDER_ENABLED', False))
        if not enabled:
            logger.debug("[Scheduler] Reminder disabled, skipping")
            return

        # Step 2: get send_time
        row = db.execute("SELECT value FROM settings WHERE key='reminder_send_time'").fetchone()
        send_time = row['value'].strip() if row and row['value'] else '09:00'

        # Step 3: check if already sent today
        row = db.execute("SELECT value FROM settings WHERE key='reminder_last_sent_date'").fetchone()
        if row and row['value'] == today:
            return

        # Step 4: check time
        if current_time < send_time:
            return

        logger.info("[Scheduler] Triggered at %s, sending reminder email", current_time)

        # Step 5: get days_before
        row = db.execute("SELECT value FROM settings WHERE key='reminder_days_before'").fetchone()
        days_before = int(row['value']) if row and row['value'] else int(app.config.get('REMINDER_DAYS_BEFORE', 30))
        deadline = (now + timedelta(days=days_before)).strftime('%Y-%m-%d')

        # Step 6: query expiring items from all three tables
        items = []
        for table, type_name in [('contracts', '合同'), ('patents', '专利'), ('insurances', '车险')]:
            end_col = 'expire_date' if table == 'patents' else 'end_date'
            rows = db.execute(
                f"SELECT * FROM {table} WHERE status!='expired' AND email_reminder=1 AND {end_col} <= ? AND {end_col} >= ?",
                (deadline, today)
            ).fetchall()
            # Debug: also check what dates exist
            all_dates = db.execute(
                f"SELECT {end_col}, status, email_reminder FROM {table} WHERE status!='expired' AND email_reminder=1 ORDER BY {end_col} ASC"
            ).fetchall()
            date_info = [f"{r[end_col]}({r['status']})" for r in all_dates[:10]]
            logger.info("[Scheduler] %s: found=%d, today=%s, deadline=%s, dates_in_db=%s",
                        table, len(rows), today, deadline, date_info)
            for r in rows:
                name = r['name'] if 'name' in r.keys() else ''
                if not name:
                    name = (r['plate_no'] if 'plate_no' in r.keys() else '') + ' ' + (r['brand'] if 'brand' in r.keys() else '')
                company = r['company'] if 'company' in r.keys() else ''
                if not company:
                    company = r['holder'] if 'holder' in r.keys() else ''
                if not company:
                    company = r['insurance_company'] if 'insurance_company' in r.keys() else ''
                contact = r['contact_person'] if 'contact_person' in r.keys() else ''
                if not contact:
                    contact = r['agent'] if 'agent' in r.keys() else ''
                start_date = r['start_date'] if 'start_date' in r.keys() else ''
                if not start_date:
                    start_date = r['application_date'] if 'application_date' in r.keys() else ''
                end_date = r['end_date'] if 'end_date' in r.keys() else ''
                if not end_date:
                    end_date = r['expire_date'] if 'expire_date' in r.keys() else ''
                items.append({
                    'type': type_name,
                    'name': name.strip(),
                    'company': company,
                    'contactPerson': contact,
                    'startDate': str(start_date),
                    'endDate': str(end_date),
                })

        # Step 7: Mark sent first to prevent duplicates
        db.execute(
            "INSERT INTO settings (key, value, updated_at) VALUES ('reminder_last_sent_date', ?, datetime('now','localtime')) "
            "ON CONFLICT(key) DO UPDATE SET value=?, updated_at=datetime('now','localtime')",
            (today, today)
        )
        db.commit()

        # Step 8: Get recipients
        row = db.execute("SELECT value FROM settings WHERE key='reminder_recipients'").fetchone()
        recipients_str = row['value'] if row and row['value'] else 'admin@suzhen.com'
        recipients = [r.strip() for r in recipients_str.split(',') if r.strip()]

        # Step 9: Read SMTP config from DB
        smtp_rows = db.execute("SELECT key, value FROM settings WHERE key LIKE 'email_%'").fetchall()
        smtp_db = {r['key']: r['value'] for r in smtp_rows}
        smtp_cfg = {
            'smtp_server': smtp_db.get('email_smtp_server') or app.config.get('EMAIL_SMTP_SERVER', 'smtp.163.com'),
            'smtp_port': int(smtp_db.get('email_smtp_port') or app.config.get('EMAIL_SMTP_PORT', 465)),
            'username': smtp_db.get('email_username') or app.config.get('EMAIL_USERNAME', ''),
            'password': smtp_db.get('email_password') or app.config.get('EMAIL_PASSWORD', ''),
            'use_tls': (smtp_db.get('email_use_tls', str(app.config.get('EMAIL_USE_TLS', False))).lower() == 'true'),
            'sender_name': smtp_db.get('email_sender_name') or app.config.get('EMAIL_SENDER_NAME', '素珍管理系统'),
        }

        logger.info("[Scheduler] SMTP: server=%s:%s user=%s tls=%s recipients=%s",
                    smtp_cfg['smtp_server'], smtp_cfg['smtp_port'],
                    smtp_cfg['username'], smtp_cfg['use_tls'], recipients)

        # Step 10: Build email body
        if items:
            item_rows_html = ''
            for item in items:
                item_rows_html += f'''
                <tr>
                    <td style="padding:8px;border:1px solid #ddd;">{item['type']}</td>
                    <td style="padding:8px;border:1px solid #ddd;">{item['name']}</td>
                    <td style="padding:8px;border:1px solid #ddd;">{item['company']}</td>
                    <td style="padding:8px;border:1px solid #ddd;">{item['contactPerson']}</td>
                    <td style="padding:8px;border:1px solid #ddd;">{item['startDate']}</td>
                    <td style="padding:8px;border:1px solid #ddd;">{item['endDate']}</td>
                </tr>'''
            body = f'''
            <html>
            <body style="font-family: sans-serif;">
                <h2>到期提醒</h2>
                <p>以下 {len(items)} 个项目将在 {days_before} 天内到期，请及时处理：</p>
                <table style="border-collapse:collapse;width:100%;">
                    <thead>
                        <tr style="background:#f0f0f0;">
                            <th style="padding:8px;border:1px solid #ddd;text-align:left;">类型</th>
                            <th style="padding:8px;border:1px solid #ddd;text-align:left;">名称</th>
                            <th style="padding:8px;border:1px solid #ddd;text-align:left;">公司/持有方</th>
                            <th style="padding:8px;border:1px solid #ddd;text-align:left;">联系人</th>
                            <th style="padding:8px;border:1px solid #ddd;text-align:left;">开始日期</th>
                            <th style="padding:8px;border:1px solid #ddd;text-align:left;">到期日期</th>
                        </tr>
                    </thead>
                    <tbody>{item_rows_html}</tbody>
                </table>
                <p style="color:#999;font-size:12px;">此邮件由素珍管理系统自动发送。</p>
            </body>
            </html>
            '''
            subject = f'【素珍管理系统】到期提醒 - {len(items)} 个项目即将到期'
        else:
            body = f'<h2>到期提醒</h2><p>未来 {days_before} 天内没有需要提醒的到期项目。</p><p style="color:#999;font-size:12px;">此邮件由素珍管理系统自动发送。</p>'
            subject = '【素珍管理系统】到期提醒 - 无到期项目'

        # Step 11: Send via send_email_direct (same path as manual test)
        with app.app_context():
            from services.email_service import send_email_direct
            success, msg = send_email_direct(recipients, subject, body, smtp_cfg)

        if success:
            logger.info("[Scheduler] Reminder email sent: %d items, %s", len(items), msg)
            _write_system_log(db, '自动发送到期提醒', '邮件服务', 'info',
                              f'到期提醒邮件发送成功 → {recipients_str}，{len(items)} 个到期项目（{msg}）')
        else:
            logger.warning("[Scheduler] Reminder email failed: %s", msg)
            _write_system_log(db, '自动发送到期提醒', '邮件服务', 'error',
                              f'到期提醒邮件发送失败 → {recipients_str}：{msg}')
            # Reset so we retry next tick
            db.execute("DELETE FROM settings WHERE key='reminder_last_sent_date'")
            db.commit()

    except Exception as e:
        logger.error("[Scheduler] Exception: %s", e, exc_info=True)
        if db:
            try:
                _write_system_log(db, '自动提醒异常', '邮件服务', 'error', f'调度器异常: {str(e)}')
            except Exception:
                pass
    finally:
        if db:
            db.close()


def init_scheduler(app):
    global _scheduler
    # Only skip if scheduler is actually running in THIS process
    # (gunicorn fork copies the global but the thread is dead)
    if _scheduler is not None:
        try:
            if _scheduler.running:
                return
        except Exception:
            pass
        _scheduler = None

    # Flask debug reloader guard
    is_debug = app.config.get('DEBUG', False)
    werkzeug_run = os.environ.get('WERKZEUG_RUN_MAIN')
    if is_debug:
        if werkzeug_run is None:
            logger.info("Skipping scheduler init in Flask reloader parent (no WERKZEUG_RUN_MAIN)")
            return
        if werkzeug_run != 'true':
            logger.info("Skipping scheduler init in Flask reloader parent (WERKZEUG_RUN_MAIN=%s)", werkzeug_run)
            return

    # Lock file for gunicorn multi-worker.
    # Includes PID + startup timestamp so container restarts don't
    # confuse the new process with the old one (same PID in Docker).
    db_path = app.config.get('DATABASE_PATH', 'backend/database/suzhen.db')
    if not os.path.isabs(db_path):
        db_path = os.path.join(app.root_path, '..', db_path)
    lock_dir = os.path.dirname(os.path.normpath(db_path))
    lock_file = os.path.join(lock_dir, 'scheduler.lock')
    my_start_time = int(time.time())

    lock_acquired = False
    try:
        fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, f"{os.getpid()}|{my_start_time}".encode())
        os.close(fd)
        lock_acquired = True
    except FileExistsError:
        try:
            with open(lock_file, 'r') as f:
                content = f.read().strip()
            parts = content.split('|')
            old_pid = int(parts[0])
            old_start = int(parts[1]) if len(parts) > 1 else 0
            if _is_process_running(old_pid) and old_start == my_start_time:
                logger.info("Scheduler already running (PID %s), skipping", old_pid)
                return
            else:
                logger.info("Removing stale lock file (PID %s, old_start=%s, my_start=%s)",
                            old_pid, old_start, my_start_time)
                os.remove(lock_file)
                fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, f"{os.getpid()}|{my_start_time}".encode())
                os.close(fd)
                lock_acquired = True
        except (ValueError, FileNotFoundError):
            if os.path.exists(lock_file):
                os.remove(lock_file)
            fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f"{os.getpid()}|{my_start_time}".encode())
            os.close(fd)
            lock_acquired = True

    if not lock_acquired:
        logger.warning("Failed to acquire scheduler lock, skipping")
        return

    try:
        _scheduler = BackgroundScheduler(daemon=True, timezone='Asia/Shanghai')
        _scheduler.add_job(
            lambda: _check_and_send_reminders(app),
            'interval', seconds=60, id='email_reminder',
            name='Email Reminder Check', misfire_grace_time=120,
        )
        _scheduler.start()

        logger.info("Email reminder scheduler started (PID=%s, interval=60s)", os.getpid())

        # Write startup log to DB
        try:
            db = _get_db_connection(app)
            _write_system_log(db, '调度器启动', '邮件服务', 'info',
                              f'定时邮件提醒调度器已启动，每60秒检查一次（PID={os.getpid()}）')
            db.close()
        except Exception as e:
            logger.warning("Failed to write scheduler startup log: %s", e)

    except Exception as e:
        logger.error("Failed to start scheduler: %s", e, exc_info=True)
        _scheduler = None
        if os.path.exists(lock_file):
            try:
                os.remove(lock_file)
            except Exception:
                pass


def _is_process_running(pid):
    """Check if a process with the given PID is actually running.

    On Windows, os.kill(pid, 0) is unreliable. We check tasklist instead.
    """
    if sys.platform != 'win32':
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    try:
        import subprocess
        result = subprocess.run(
            ['tasklist', '/FI', f'PID eq {pid}', '/NH'],
            capture_output=True, text=True, timeout=5
        )
        return str(pid) in result.stdout and 'python' in result.stdout.lower()
    except Exception:
        return True  # assume running if we can't check


def reset_send_state():
    import os as _os
    from flask import current_app as _current_app
    try:
        db_path = _current_app.config.get('DATABASE_PATH', 'backend/database/suzhen.db')
        if not _os.path.isabs(db_path):
            db_path = _os.path.join(_current_app.root_path, '..', db_path)
        db_path = _os.path.normpath(db_path)
        conn = sqlite3.connect(db_path)
        conn.execute("DELETE FROM settings WHERE key='reminder_last_sent_date'")
        conn.commit()
        conn.close()
        logger.info("Scheduler send state reset")
    except Exception as e:
        logger.error("Failed to reset send state: %s", e)


def shutdown_scheduler():
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Email reminder scheduler stopped")
