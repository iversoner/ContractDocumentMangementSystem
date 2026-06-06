"""
系统配置 API
"""
from flask import Blueprint, request, jsonify, g

from database.db import get_db, beijing_now
from services.email_service import send_email
from services.log_service import write_log
from middleware.auth_middleware import login_required, admin_required

setting_bp = Blueprint('setting', __name__)


@setting_bp.route('', methods=['GET'])
@login_required
def get_settings():
    db = get_db()
    rows = db.execute("SELECT key, value, updated_at FROM settings").fetchall()
    settings = {r['key']: r['value'] for r in rows}

    # 合并配置文件中的默认值
    from flask import current_app
    result = {
        'email': {
            'smtpServer': settings.get('email_smtp_server', current_app.config.get('EMAIL_SMTP_SERVER', '')),
            'smtpPort': int(settings.get('email_smtp_port', current_app.config.get('EMAIL_SMTP_PORT', 587))),
            'username': settings.get('email_username', current_app.config.get('EMAIL_USERNAME', '')),
            'password': settings.get('email_password', '') or current_app.config.get('EMAIL_PASSWORD', ''),
            'useTLS': settings.get('email_use_tls', str(current_app.config.get('EMAIL_USE_TLS', True))).lower() == 'true',
            'senderName': settings.get('email_sender_name', current_app.config.get('EMAIL_SENDER_NAME', '')),
        },
        'database': {
            'type': 'sqlite3',
            'path': settings.get('db_path', current_app.config.get('DATABASE_PATH', '')),
            'backupEnabled': settings.get('db_backup_enabled', 'false').lower() == 'true',
            'backupInterval': settings.get('db_backup_interval', 'daily'),
        },
        'reminder': {
            'enabled': settings.get('reminder_enabled', str(current_app.config.get('REMINDER_ENABLED', False))).lower() == 'true',
            'daysBefore': int(settings.get('reminder_days_before', current_app.config.get('REMINDER_DAYS_BEFORE', 30))),
            'sendTime': settings.get('reminder_send_time', '09:00'),
            'recipients': settings.get('reminder_recipients', 'admin@suzhen.com'),
        },
    }
    return jsonify({'success': True, 'data': result})


@setting_bp.route('', methods=['PUT'])
@admin_required
def update_settings():
    data = request.get_json() or {}
    db = get_db()

    # 读取旧配置用于对比日志
    old_rows = db.execute("SELECT key, value FROM settings").fetchall()
    old_settings = {r['key']: r['value'] for r in old_rows}

    updates = []
    detail_parts = []

    if 'email' in data:
        e = data['email']
        email_keys = [
            ('email_smtp_server', 'SMTP服务器', str(e.get('smtpServer', ''))),
            ('email_smtp_port', 'SMTP端口', str(e.get('smtpPort', 587))),
            ('email_username', '邮箱账号', str(e.get('username', ''))),
            ('email_use_tls', 'TLS', str(e.get('useTLS', True)).lower()),
            ('email_sender_name', '发件人名称', str(e.get('senderName', ''))),
        ]
        for key, label, new_val in email_keys:
            old_val = old_settings.get(key, '')
            if old_val != new_val:
                detail_parts.append(f'{label}: "{old_val}" → "{new_val}"')
            updates.append((key, new_val))
        # 密码单独处理（仅非空时更新）
        pwd = str(e.get('password', ''))
        if pwd:
            old_pwd = old_settings.get('email_password', '')
            if old_pwd != pwd:
                detail_parts.append('邮箱密码: 已更新')
            updates.append(('email_password', pwd))

    if 'database' in data:
        d = data['database']
        db_keys = [
            ('db_path', '数据库路径', str(d.get('path', ''))),
            ('db_backup_enabled', '备份启用', str(d.get('backupEnabled', False)).lower()),
            ('db_backup_interval', '备份间隔', str(d.get('backupInterval', 'daily'))),
        ]
        for key, label, new_val in db_keys:
            old_val = old_settings.get(key, '')
            if old_val != new_val:
                detail_parts.append(f'{label}: "{old_val}" → "{new_val}"')
            updates.append((key, new_val))

    if 'reminder' in data:
        r = data['reminder']
        reminder_keys = [
            ('reminder_enabled', '提醒开关', str(r.get('enabled', False)).lower()),
            ('reminder_days_before', '提前天数', str(r.get('daysBefore', 30))),
            ('reminder_send_time', '发送时间', str(r.get('sendTime', '09:00'))),
            ('reminder_recipients', '收件人', str(r.get('recipients', ''))),
        ]
        for key, label, new_val in reminder_keys:
            old_val = old_settings.get(key, '')
            if old_val != new_val:
                detail_parts.append(f'{label}: "{old_val}" → "{new_val}"')
            updates.append((key, new_val))

        # 重置调度器状态
        try:
            from services.scheduler_service import reset_send_state
            reset_send_state()
            detail_parts.append('调度器发送状态已重置（下次心跳重新评估）')
        except ImportError:
            pass

    for key, value in updates:
        db.execute(
            "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, beijing_now()) "
            "ON CONFLICT(key) DO UPDATE SET value=?, updated_at=beijing_now()",
            (key, value, value)
        )
    db.commit()

    log_detail = '；'.join(detail_parts) if detail_parts else '配置已保存（无变更）'
    write_log(action='修改配置', module='系统配置', detail=log_detail,
              user_id=g.user_id, username=g.username)

    return jsonify({'success': True, 'message': '配置已保存'})


@setting_bp.route('/test-email', methods=['POST'])
@admin_required
def test_email():
    data = request.get_json() or {}
    to_email = data.get('email', current_app.config.get('EMAIL_USERNAME', ''))

    # 优先使用页面传来的 SMTP 配置，否则用数据库/配置文件的值
    smtp_config = data.get('smtpConfig', None)
    if smtp_config:
        from services.email_service import send_email_direct
        # 前端传驼峰命名，转为下划线
        cfg = {
            'smtp_server': smtp_config.get('smtpServer', ''),
            'smtp_port': int(smtp_config.get('smtpPort', 587)),
            'username': smtp_config.get('username', ''),
            'password': smtp_config.get('password', ''),
            'use_tls': smtp_config.get('useTLS', True),
            'sender_name': smtp_config.get('senderName', ''),
        }
        success, message = send_email_direct(
            [to_email],
            '【素珍管理系统】邮件测试',
            '<h2>邮件发送测试</h2><p>如果您收到此邮件,说明邮箱服务配置正确。</p><p style="color:#999">此邮件由素珍管理系统自动发送。</p>',
            cfg
        )
    else:
        success, message = send_email(
            [to_email],
            '【素珍管理系统】邮件测试',
            '<h2>邮件发送测试</h2><p>如果您收到此邮件,说明邮箱服务配置正确。</p><p style="color:#999">此邮件由素珍管理系统自动发送。</p>'
        )

    if success:
        write_log(action='测试邮件', module='邮件服务', detail=f'测试邮件发送成功 → {to_email}',
                  user_id=g.user_id, username=g.username)
        return jsonify({'success': True, 'message': message})
    else:
        write_log(action='测试邮件', module='邮件服务', level='error',
                  detail=f'测试邮件发送失败 → {to_email}: {message}',
                  user_id=g.user_id, username=g.username)
        return jsonify({'success': False, 'message': message}), 500


# 需要从 flask 导入 current_app（放在函数里避免循环导入）
from flask import current_app
