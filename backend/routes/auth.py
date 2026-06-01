"""
认证接口：登录、登出、获取当前用户
"""
from flask import Blueprint, request, jsonify, g

from database.db import get_db
from services.auth_service import check_password, generate_token
from services.log_service import write_log
from middleware.auth_middleware import login_required

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    """用户登录"""
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({'success': False, 'message': '请输入用户名和密码'}), 400

    db = get_db()
    user = db.execute(
        "SELECT id, username, password_hash, display_name, role, status FROM users WHERE username = ?",
        (username,)
    ).fetchone()

    if not user:
        return jsonify({'success': False, 'message': '用户名或密码错误'}), 401

    if user['status'] != 'active':
        return jsonify({'success': False, 'message': '账号已被禁用，请联系管理员'}), 403

    if not check_password(password, user['password_hash']):
        write_log(action='登录失败', module='认证', level='warning',
                  detail=f'用户 {username} 密码错误', username=username)
        return jsonify({'success': False, 'message': '用户名或密码错误'}), 401

    token = generate_token(user['id'], user['username'], user['role'])
    write_log(action='登录系统', module='认证', detail=f'用户 {username} 登录成功',
              user_id=user['id'], username=username)

    return jsonify({
        'success': True,
        'message': '登录成功',
        'data': {
            'token': token,
            'user': {
                'id': user['id'],
                'username': user['username'],
                'displayName': user['display_name'],
                'role': user['role'],
            }
        }
    })


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """登出"""
    write_log(action='登出系统', module='认证', detail=f'用户 {g.username} 登出',
              user_id=g.user_id, username=g.username)
    return jsonify({'success': True, 'message': '已登出'})


@auth_bp.route('/me', methods=['GET'])
@login_required
def me():
    """获取当前登录用户信息"""
    db = get_db()
    user = db.execute(
        "SELECT id, username, display_name, email, role, status, created_at FROM users WHERE id = ?",
        (g.user_id,)
    ).fetchone()

    if not user:
        return jsonify({'success': False, 'message': '用户不存在'}), 404

    return jsonify({
        'success': True,
        'data': {
            'id': user['id'],
            'username': user['username'],
            'displayName': user['display_name'],
            'email': user['email'],
            'role': user['role'],
            'status': user['status'],
            'createdAt': str(user['created_at']),
        }
    })
