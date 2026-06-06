"""
JWT 鉴权装饰器
"""
from functools import wraps
from flask import request, g, jsonify
from services.auth_service import verify_token


def _get_token():
    """从 Authorization header 或 query param 中提取 token"""
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header[7:]
    # <a> 标签下载无法设置 header，从 query param 获取
    return request.args.get('token', '')


def login_required(f):
    """装饰器：要求请求携带有效的 JWT token"""

    @wraps(f)
    def decorated(*args, **kwargs):
        token = _get_token()
        if not token:
            return jsonify({'success': False, 'message': '未提供认证令牌'}), 401

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
