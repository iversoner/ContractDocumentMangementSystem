"""
JWT 鉴权装饰器
"""
from functools import wraps
from flask import request, g, jsonify
from services.auth_service import verify_token


def login_required(f):
    """装饰器：要求请求携带有效的 JWT token"""

    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'message': '未提供认证令牌'}), 401

        token = auth_header[7:]
        payload = verify_token(token)
        if payload is None:
            return jsonify({'success': False, 'message': '令牌无效或已过期，请重新登录'}), 401

        g.user_id = payload.get('user_id')
        g.username = payload.get('username')
        g.role = payload.get('role')
        return f(*args, **kwargs)

    return decorated


def admin_required(f):
    """装饰器：要求管理员角色"""

    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if g.role != '管理员':
            return jsonify({'success': False, 'message': '权限不足，需要管理员角色'}), 403
        return f(*args, **kwargs)

    return decorated
