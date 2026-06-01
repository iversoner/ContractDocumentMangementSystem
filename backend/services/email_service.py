"""
邮件服务
通过 SMTP 发送通知邮件
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from flask import current_app


def get_email_config():
    """从数据库 settings 表 + Flask config 读取邮件配置（数据库优先）"""
    config = {
        'smtp_server': current_app.config.get('EMAIL_SMTP_SERVER', 'smtp.example.com'),
        'smtp_port': current_app.config.get('EMAIL_SMTP_PORT', 587),
        'username': current_app.config.get('EMAIL_USERNAME', ''),
        'password': current_app.config.get('EMAIL_PASSWORD', ''),
        'sender_name': current_app.config.get('EMAIL_SENDER_NAME', '素珍管理系统'),
        'use_tls': current_app.config.get('EMAIL_USE_TLS', True),
    }
    # 数据库 settings 表覆盖（用户在页面上保存的配置）
    try:
        from database.db import get_db
        db = get_db()
        rows = db.execute(
            "SELECT key, value FROM settings WHERE key LIKE 'email_%'"
        ).fetchall()
        db_overrides = {r['key']: r['value'] for r in rows}
        if db_overrides.get('email_smtp_server'):
            config['smtp_server'] = db_overrides['email_smtp_server']
        if db_overrides.get('email_smtp_port'):
            config['smtp_port'] = int(db_overrides['email_smtp_port'])
        if db_overrides.get('email_username'):
            config['username'] = db_overrides['email_username']
        if db_overrides.get('email_password'):
            config['password'] = db_overrides['email_password']
        if db_overrides.get('email_use_tls'):
            config['use_tls'] = db_overrides['email_use_tls'].lower() == 'true'
        if db_overrides.get('email_sender_name'):
            config['sender_name'] = db_overrides['email_sender_name']
    except Exception:
        pass  # 数据库未初始化时回退到 config.yaml
    return config


def send_email(to_emails: list, subject: str, body: str) -> tuple:
    """发送邮件，返回 (success: bool, message: str)"""
    config = get_email_config()

    if not config['username'] or not config['password']:
        return False, '邮箱账号或密码未配置'

    if not to_emails:
        return False, '收件人地址为空'

    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = f"{config['sender_name']} <{config['username']}>"
        msg['To'] = ', '.join(to_emails)
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html', 'utf-8'))

        if config['use_tls']:
            server = smtplib.SMTP(config['smtp_server'], config['smtp_port'], timeout=10)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(config['smtp_server'], config['smtp_port'], timeout=10)

        server.login(config['username'], config['password'])
        server.sendmail(config['username'], to_emails, msg.as_string())
        server.quit()

        return True, f'邮件已发送至 {len(to_emails)} 个收件人'
    except smtplib.SMTPAuthenticationError:
        return False, '邮箱认证失败，请检查账号密码'
    except smtplib.SMTPConnectError:
        return False, f'无法连接到邮件服务器 {config["smtp_server"]}:{config["smtp_port"]}'
    except Exception as e:
        return False, f'邮件发送失败: {str(e)}'


def send_email_direct(to_emails: list, subject: str, body: str, config: dict) -> tuple:
    """直接使用传入的 SMTP 配置发送邮件（不读数据库），返回 (success, message)"""
    if not config.get('username') or not config.get('password'):
        return False, '邮箱账号或密码未配置'
    if not to_emails:
        return False, '收件人地址为空'

    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = f"{config.get('sender_name', '')} <{config['username']}>"
        msg['To'] = ', '.join(to_emails)
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'html', 'utf-8'))

        if config.get('use_tls', True):
            server = smtplib.SMTP(config['smtp_server'], int(config.get('smtp_port', 587)), timeout=10)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(config['smtp_server'], int(config.get('smtp_port', 465)), timeout=10)

        server.login(config['username'], config['password'])
        server.sendmail(config['username'], to_emails, msg.as_string())
        server.quit()

        return True, f'邮件已发送至 {len(to_emails)} 个收件人'
    except smtplib.SMTPAuthenticationError:
        return False, '邮箱认证失败，请检查账号密码（授权码）'
    except smtplib.SMTPConnectError:
        return False, f'无法连接到邮件服务器 {config["smtp_server"]}:{config["smtp_port"]}'
    except Exception as e:
        return False, f'邮件发送失败: {str(e)}'


def send_reminder_email(items: list, days_before: int) -> tuple:
    """发送到期提醒邮件"""
    if not items:
        return False, '没有需要提醒的到期项目'

    # 从数据库读取提醒配置（收件人、天数等）
    recipients_str = 'admin@suzhen.com'
    try:
        from database.db import get_db
        db = get_db()
        row = db.execute("SELECT value FROM settings WHERE key='reminder_recipients'").fetchone()
        if row and row['value']:
            recipients_str = row['value']
        row2 = db.execute("SELECT value FROM settings WHERE key='reminder_days_before'").fetchone()
        if row2 and row2['value']:
            days_before = int(row2['value'])
    except Exception:
        pass

    recipients = [r.strip() for r in recipients_str.split(',') if r.strip()]

    subject = f'【素珍管理系统】到期提醒 - {len(items)} 个项目即将到期'

    rows = ''
    for item in items:
        company = item.get('company', '')
        contact = item.get('contactPerson', '')
        start = item.get('startDate', '')
        end = item.get('endDate', '')
        rows += f'''
        <tr>
            <td style="padding:8px;border:1px solid #ddd;">{item.get('type', '')}</td>
            <td style="padding:8px;border:1px solid #ddd;">{item.get('name', '')}</td>
            <td style="padding:8px;border:1px solid #ddd;">{company}</td>
            <td style="padding:8px;border:1px solid #ddd;">{contact}</td>
            <td style="padding:8px;border:1px solid #ddd;">{start}</td>
            <td style="padding:8px;border:1px solid #ddd;">{end}</td>
        </tr>
        '''

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
            <tbody>{rows}</tbody>
        </table>
        <p style="color:#999;font-size:12px;">此邮件由素珍管理系统自动发送。</p>
    </body>
    </html>
    '''

    return send_email(recipients, subject, body)
