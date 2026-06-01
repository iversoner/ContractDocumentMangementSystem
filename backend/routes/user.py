"""
用户管理 API
"""
from flask import Blueprint, request, jsonify, g

from database.db import get_db
from services.auth_service import hash_password
from services.log_service import write_log
from middleware.auth_middleware import login_required, admin_required

user_bp = Blueprint('user', __name__)


def _row_to_dict(r) -> dict:
    return {
        'id': r['id'],
        'username': r['username'],
        'displayName': r['display_name'],
        'email': r['email'] or '',
        'role': r['role'],
        'status': r['status'],
        'createdAt': str(r['created_at']),
    }


@user_bp.route('', methods=['GET'])
@login_required
def list_users():
    db = get_db()
    role = request.args.get('role', '').strip()
    status = request.args.get('status', '').strip()
    keyword = request.args.get('keyword', '').strip()
    page = max(1, request.args.get('page', 1, type=int))
    page_size = max(1, min(100, request.args.get('pageSize', 10, type=int)))

    where = []
    params = []
    if role:
        where.append("role = ?")
        params.append(role)
    if status:
        where.append("status = ?")
        params.append(status)
    if keyword:
        where.append("(username LIKE ? OR display_name LIKE ?)")
        params.extend([f'%{keyword}%', f'%{keyword}%'])

    # 非管理员只能看到同角色用户
    if g.role != '管理员':
        where.append("role = ?")
        params.append(g.role)

    where_sql = (' AND '.join(where)) if where else '1=1'

    total = db.execute(f"SELECT COUNT(*) FROM users WHERE {where_sql}", params).fetchone()[0]
    rows = db.execute(
        f"SELECT * FROM users WHERE {where_sql} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        params + [page_size, (page - 1) * page_size]
    ).fetchall()

    return jsonify({
        'success': True,
        'data': {
            'items': [_row_to_dict(r) for r in rows],
            'total': total,
            'page': page,
            'pageSize': page_size,
        }
    })


@user_bp.route('', methods=['POST'])
@admin_required
def create_user():
    data = request.get_json() or {}
    required = ['username', 'displayName', 'password']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'success': False, 'message': f'缺少必填字段: {", ".join(missing)}'}), 400

    db = get_db()
    existing = db.execute("SELECT id FROM users WHERE username = ?", (data['username'],)).fetchone()
    if existing:
        return jsonify({'success': False, 'message': '用户名已存在'}), 409

    password_hash = hash_password(data['password'])
    cursor = db.execute(
        "INSERT INTO users (username, password_hash, display_name, email, role) VALUES (?, ?, ?, ?, ?)",
        (data['username'], password_hash, data['displayName'],
         data.get('email', ''), data.get('role', '业务员'))
    )
    db.commit()
    new_id = cursor.lastrowid
    write_log(action='新增用户', module='用户管理', detail=f'新增用户「{data["displayName"]}」({data["username"]})',
              user_id=g.user_id, username=g.username)

    r = db.execute("SELECT * FROM users WHERE id = ?", (new_id,)).fetchone()
    return jsonify({'success': True, 'message': '用户已添加', 'data': _row_to_dict(r)}), 201


@user_bp.route('/<int:id>', methods=['PUT'])
@admin_required
def update_user(id):
    db = get_db()
    old = db.execute("SELECT * FROM users WHERE id = ?", (id,)).fetchone()
    if not old:
        return jsonify({'success': False, 'message': '用户不存在'}), 404

    data = request.get_json() or {}
    db.execute(
        "UPDATE users SET display_name=?, email=?, role=?, status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (data.get('displayName', old['display_name']),
         data.get('email', old['email'] or ''),
         data.get('role', old['role']),
         data.get('status', old['status']),
         id)
    )
    db.commit()
    write_log(action='编辑用户', module='用户管理', detail=f'编辑用户「{old["display_name"]}」({old["username"]})',
              user_id=g.user_id, username=g.username)

    r = db.execute("SELECT * FROM users WHERE id = ?", (id,)).fetchone()
    return jsonify({'success': True, 'message': '用户已更新', 'data': _row_to_dict(r)})


@user_bp.route('/<int:id>/reset-password', methods=['PUT'])
@admin_required
def reset_password(id):
    db = get_db()
    old = db.execute("SELECT * FROM users WHERE id = ?", (id,)).fetchone()
    if not old:
        return jsonify({'success': False, 'message': '用户不存在'}), 404

    data = request.get_json() or {}
    new_password = data.get('password', '123456')
    password_hash = hash_password(new_password)
    db.execute("UPDATE users SET password_hash=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (password_hash, id))
    db.commit()
    write_log(action='重置密码', module='用户管理',
              detail=f'重置用户「{old["display_name"]}」({old["username"]})的密码',
              user_id=g.user_id, username=g.username)

    return jsonify({'success': True, 'message': f'密码已重置为: {new_password}'})


@user_bp.route('/<int:id>', methods=['DELETE'])
@admin_required
def delete_user(id):
    db = get_db()
    old = db.execute("SELECT * FROM users WHERE id = ?", (id,)).fetchone()
    if not old:
        return jsonify({'success': False, 'message': '用户不存在'}), 404
    if old['role'] == '管理员':
        return jsonify({'success': False, 'message': '不能删除管理员账号'}), 403
    db.execute("DELETE FROM users WHERE id = ?", (id,))
    db.commit()
    write_log(action='删除用户', module='用户管理', detail=f'删除用户「{old["display_name"]}」({old["username"]})',
              user_id=g.user_id, username=g.username)
    return jsonify({'success': True, 'message': '用户已删除'})
