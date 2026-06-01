"""
系统日志 API
"""
from flask import Blueprint, request, jsonify, g

from database.db import get_db
from middleware.auth_middleware import login_required, admin_required

log_bp = Blueprint('log', __name__)


@log_bp.route('', methods=['GET'])
@login_required
def list_logs():
    db = get_db()
    level = request.args.get('level', '').strip()
    module = request.args.get('module', '').strip()
    keyword = request.args.get('keyword', '').strip()
    page = max(1, request.args.get('page', 1, type=int))
    page_size = max(1, min(100, request.args.get('pageSize', 20, type=int)))

    where = []
    params = []
    if level:
        where.append("level = ?")
        params.append(level)
    if module:
        where.append("module = ?")
        params.append(module)
    if keyword:
        where.append("(action LIKE ? OR detail LIKE ? OR username LIKE ?)")
        params.extend([f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'])

    # 非管理员只能看到自己的日志
    if g.role != '管理员':
        where.append("user_id = ?")
        params.append(g.user_id)

    where_sql = (' AND '.join(where)) if where else '1=1'

    total = db.execute(f"SELECT COUNT(*) FROM operation_logs WHERE {where_sql}", params).fetchone()[0]
    rows = db.execute(
        f"SELECT * FROM operation_logs WHERE {where_sql} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        params + [page_size, (page - 1) * page_size]
    ).fetchall()

    items = [{
        'id': r['id'],
        'userId': r['user_id'],
        'username': r['username'] or '',
        'action': r['action'],
        'module': r['module'],
        'level': r['level'],
        'detail': r['detail'] or '',
        'ipAddress': r['ip_address'] or '',
        'createdAt': str(r['created_at']),
    } for r in rows]

    return jsonify({
        'success': True,
        'data': {
            'items': items,
            'total': total,
            'page': page,
            'pageSize': page_size,
        }
    })


@log_bp.route('', methods=['DELETE'])
@admin_required
def clear_logs():
    db = get_db()
    db.execute("DELETE FROM operation_logs")
    db.commit()
    return jsonify({'success': True, 'message': '日志已清空'})
