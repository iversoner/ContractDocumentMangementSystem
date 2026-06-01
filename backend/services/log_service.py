"""
统一日志服务
所有业务操作通过此模块写入 operation_logs 表
"""
from flask import request, g
from database.db import get_db
from database.db import beijing_now


def write_log(action: str, module: str, level: str = 'info', detail: str = '', user_id: int = None, username: str = None):
    """写入操作日志"""
    db = get_db()
    if user_id is None:
        user_id = g.get('user_id', None)
    if username is None:
        username = g.get('username', 'system')
    ip_address = request.remote_addr if request else ''

    db.execute(
        "INSERT INTO operation_logs (user_id, username, action, module, level, detail, ip_address, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, beijing_now())",
        (user_id, username, action, module, level, detail, ip_address)
    )
    db.commit()
