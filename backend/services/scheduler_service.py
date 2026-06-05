"""
Background scheduler for automatic email reminders.
Uses APScheduler to periodically check and send expiry reminder emails.
"""
import os
import sqlite3
import logging
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger(__name__)

_scheduler = None
_last_sent_date = None  # prevent duplicate sends on the same day


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


def _check_and_send_reminders(app):
    """Check reminder settings and send emails if conditions are met."""
    global _last_sent_date

    db = None
    try:
        db = _get_db_connection(app)

        # Check if reminder is enabled
        row = db.execute(
            "SELECT value FROM settings WHERE key='reminder_enabled'"
        ).fetchone()
        if not row or row['value'].lower() != 'true':
            return

        # Get send_time setting
        row = db.execute(
            "SELECT value FROM settings WHERE key='reminder_send_time'"
        ).fetchone()
        send_time = row['value'].strip() if row and row['value'] else '09:00'

        # Get days_before setting
        row = db.execute(
            "SELECT value FROM settings WHERE key='reminder_days_before'"
        ).fetchone()
        days_before = int(row['value']) if row and row['value'] else 30

        # Check if current Beijing time matches send_time
        now = _beijing_now()
        current_time = now.strftime('%H:%M')
        today = now.strftime('%Y-%m-%d')

        # Only send once per day
        if _last_sent_date == today:
            return

        if current_time != send_time:
            return

        logger.info(
            "Reminder check: time matched %s, querying items expiring within %s days",
            send_time, days_before
        )

        # Query expiring items from all three modules
        cutoff_date = (now + timedelta(days=days_before)).strftime('%Y-%m-%d')

        items = []

        # Contracts
        contracts = db.execute(
            """SELECT name, company, agent as contactPerson, end_date as endDate,
               'Contract' as type, start_date as startDate
               FROM contracts
               WHERE status = 'active'
               AND email_reminder = 1
               AND end_date <= ?
               AND end_date >= ?""",
            (cutoff_date, today),
        ).fetchall()
        for r in contracts:
            items.append(dict(r))

        # Patents
        patents = db.execute(
            """SELECT name, holder as company, agent as contactPerson,
               expire_date as endDate, 'Patent' as type, application_date as startDate
               FROM patents
               WHERE status = 'active'
               AND email_reminder = 1
               AND expire_date <= ?
               AND expire_date >= ?""",
            (cutoff_date, today),
        ).fetchall()
        for r in patents:
            items.append(dict(r))

        # Insurances
        insurances = db.execute(
            """SELECT plate_no as name, brand as company, agent as contactPerson,
               end_date as endDate, 'Insurance' as type, start_date as startDate
               FROM insurances
               WHERE status = 'active'
               AND email_reminder = 1
               AND end_date <= ?
               AND end_date >= ?""",
            (cutoff_date, today),
        ).fetchall()
        for r in insurances:
            items.append(dict(r))

        if not items:
            logger.info("Reminder check: no expiring items found")
            _last_sent_date = today
            return

        # Send reminder email (with app context for Flask config access)
        with app.app_context():
            from services.email_service import send_reminder_email
            success, msg = send_reminder_email(items, days_before)

        if success:
            logger.info("Reminder email sent: %s", msg)
            _last_sent_date = today
        else:
            logger.warning("Reminder email failed: %s", msg)

    except Exception as e:
        logger.error("Reminder check error: %s", e, exc_info=True)
    finally:
        if db:
            db.close()


def init_scheduler(app):
    """Initialize and start the background scheduler.

    Safe to call multiple times (idempotent).
    Uses a file lock to ensure only one scheduler runs across gunicorn workers.
    """
    global _scheduler

    if _scheduler is not None:
        return

    # Use a lock file to prevent duplicate schedulers (important for gunicorn)
    db_path = app.config.get('DATABASE_PATH', 'backend/database/suzhen.db')
    if not os.path.isabs(db_path):
        db_path = os.path.join(app.root_path, '..', db_path)
    lock_dir = os.path.dirname(os.path.normpath(db_path))
    lock_file = os.path.join(lock_dir, 'scheduler.lock')

    # Use atomic file creation to prevent race conditions between gunicorn workers
    try:
        fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
    except FileExistsError:
        # Another worker already holds the lock, check if it's alive
        try:
            with open(lock_file, 'r') as f:
                pid = int(f.read().strip())
            try:
                os.kill(pid, 0)
                logger.info("Scheduler already running (PID %s), skipping", pid)
                return
            except OSError:
                # Stale lock, remove and retry
                os.remove(lock_file)
                fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, str(os.getpid()).encode())
                os.close(fd)
        except (ValueError, FileNotFoundError):
            if os.path.exists(lock_file):
                os.remove(lock_file)
            fd = os.open(lock_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)

    try:
        _scheduler = BackgroundScheduler(
            daemon=True,
            timezone='Asia/Shanghai',
        )

        _scheduler.add_job(
            lambda: _check_and_send_reminders(app),
            'interval',
            seconds=60,
            id='email_reminder',
            name='Email Reminder Check',
            misfire_grace_time=120,
        )

        _scheduler.start()

        with open(lock_file, 'w') as f:
            f.write(str(os.getpid()))

        logger.info("Email reminder scheduler started (check interval: 60s)")
    except Exception as e:
        logger.error("Failed to start scheduler: %s", e, exc_info=True)
        _scheduler = None


def shutdown_scheduler():
    """Stop the scheduler gracefully."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Email reminder scheduler stopped")
