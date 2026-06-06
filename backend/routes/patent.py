"""
专利管理 API
"""
from datetime import date

from flask import Blueprint, request, jsonify, g

from database.db import get_db
from database.db import utc_to_beijing, host_file_path
from services.log_service import write_log
from middleware.auth_middleware import login_required, admin_required

patent_bp = Blueprint('patent', __name__)


def _calc_status(expire_date: str) -> str:
    today = date.today()
    try:
        ed = date.fromisoformat(expire_date)
    except (ValueError, TypeError):
        return 'active'
    if ed < today:
        return 'expired'
    return 'active'


def _row_to_dict(r) -> dict:
    # 计算 isComplete：手动录入始终完整，扫描导入动态检查必填字段
    if 'source' in r.keys() and r['source'] == 'scan':
        is_complete = bool(
            r['name'] and r['patent_no'] and r['type'] and r['holder'] and r['agent']
            and r['application_date'] and r['expire_date']
        )
    else:
        is_complete = True

    return {
        'id': r['id'],
        'name': r['name'],
        'patentNo': r['patent_no'],
        'type': r['type'],
        'holder': r['holder'],
        'agent': r['agent'],
        'applicationDate': str(r['application_date']),
        'expireDate': str(r['expire_date']),
        'status': r['status'],
        'filePath': r['file_path'] or '',
        'fileName': r['file_name'] if 'file_name' in r.keys() else '',
        'hostFilePath': host_file_path(r['file_path'] or ''),
        'remark': r['remark'] or '',
        'createdAt': utc_to_beijing(str(r['created_at'])),
        'updatedAt': utc_to_beijing(str(r['updated_at'])),
        'source': r['source'] if 'source' in r.keys() else 'manual',
        'emailReminder': bool(r['email_reminder']) if 'email_reminder' in r.keys() else True,
        'priority': r['priority'] if 'priority' in r.keys() else '普通',
        'isComplete': is_complete,
    }


@patent_bp.route('', methods=['GET'])
@login_required
def list_patents():
    db = get_db()
    type_filter = request.args.get('type', '').strip()
    status = request.args.get('status', '').strip()
    keyword = request.args.get('keyword', '').strip()
    page = max(1, request.args.get('page', 1, type=int))
    page_size = max(1, min(100, request.args.get('pageSize', 10, type=int)))

    where = []
    params = []
    if type_filter:
        where.append("type = ?")
        params.append(type_filter)
    if status:
        where.append("status = ?")
        params.append(status)
    if keyword:
        where.append("(name LIKE ? OR patent_no LIKE ?)")
        params.extend([f'%{keyword}%', f'%{keyword}%'])

    where_sql = (' AND '.join(where)) if where else '1=1'

    # 排序（白名单防注入）
    sort_by = request.args.get('sortBy', 'created_at').strip()
    sort_order = request.args.get('sortOrder', 'desc').strip()
    SORT_WHITELIST = {
        'expire_date': 'expire_date',
        'name': 'name',
        'priority': "CASE priority WHEN '重要' THEN 0 WHEN '普通' THEN 1 WHEN '不重要' THEN 2 END",
        'created_at': 'created_at',
    }
    order_col = SORT_WHITELIST.get(sort_by, 'created_at')
    order_dir = 'DESC' if sort_order.lower() == 'desc' else 'ASC'

    total = db.execute(f"SELECT COUNT(*) FROM patents WHERE {where_sql}", params).fetchone()[0]
    rows = db.execute(
        f"SELECT * FROM patents WHERE {where_sql} ORDER BY {order_col} {order_dir} LIMIT ? OFFSET ?",
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


@patent_bp.route('/<int:id>', methods=['GET'])
@login_required
def get_patent(id):
    db = get_db()
    r = db.execute("SELECT * FROM patents WHERE id = ?", (id,)).fetchone()
    if not r:
        return jsonify({'success': False, 'message': '专利不存在'}), 404
    return jsonify({'success': True, 'data': _row_to_dict(r)})


@patent_bp.route('', methods=['POST'])
@login_required
def create_patent():
    data = request.get_json() or {}
    required = ['name', 'patentNo', 'type', 'holder', 'agent', 'applicationDate', 'expireDate']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'success': False, 'message': f'缺少必填字段: {", ".join(missing)}'}), 400

    status = _calc_status(data['expireDate'])
    db = get_db()
    cursor = db.execute(
        """INSERT INTO patents (name, patent_no, type, holder, agent, application_date, expire_date,
           status, file_path, remark, email_reminder, priority)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (data['name'], data['patentNo'], data['type'], data['holder'], data['agent'],
         data['applicationDate'], data['expireDate'], status,
         data.get('filePath', ''), data.get('remark', ''),
         1 if data.get('emailReminder', True) else 0,
         data.get('priority', '普通'))
    )
    db.commit()
    new_id = cursor.lastrowid
    write_log(action='新增专利', module='专利管理', detail=f'新增专利「{data["name"]}」(ID={new_id})',
              user_id=g.user_id, username=g.username)

    r = db.execute("SELECT * FROM patents WHERE id = ?", (new_id,)).fetchone()
    return jsonify({'success': True, 'message': '专利已添加', 'data': _row_to_dict(r)}), 201


@patent_bp.route('/<int:id>', methods=['PUT'])
@login_required
def update_patent(id):
    db = get_db()
    old = db.execute("SELECT * FROM patents WHERE id = ?", (id,)).fetchone()
    if not old:
        return jsonify({'success': False, 'message': '专利不存在'}), 404

    data = request.get_json() or {}
    status = _calc_status(data.get('expireDate', old['expire_date']))

    db.execute(
        """UPDATE patents SET name=?, patent_no=?, type=?, holder=?, agent=?,
           application_date=?, expire_date=?, status=?, file_path=?, remark=?,
           email_reminder=?, priority=?, updated_at=beijing_now() WHERE id=?""",
        (data.get('name', old['name']),
         data.get('patentNo', old['patent_no']),
         data.get('type', old['type']),
         data.get('holder', old['holder']),
         data.get('agent', old['agent']),
         data.get('applicationDate', old['application_date']),
         data.get('expireDate', old['expire_date']),
         status,
         data.get('filePath', old['file_path'] or ''),
         data.get('remark', old['remark'] or ''),
         1 if data.get('emailReminder', True) else 0,
         data.get('priority', old['priority'] if 'priority' in old.keys() else '普通'),
         id)
    )
    db.commit()
    write_log(action='编辑专利', module='专利管理', detail=f'编辑专利「{old["name"]}」(ID={id})',
              user_id=g.user_id, username=g.username)

    r = db.execute("SELECT * FROM patents WHERE id = ?", (id,)).fetchone()
    return jsonify({'success': True, 'message': '专利已更新', 'data': _row_to_dict(r)})


@patent_bp.route('/batch', methods=['PUT'])
@login_required
def batch_update_patents():
    """批量更新专利字段"""
    data = request.get_json() or {}
    ids = data.get('ids', [])
    field = data.get('field', '')
    value = data.get('value')

    if not ids or not field:
        return jsonify({'success': False, 'message': '缺少 ids 或 field 参数'}), 400

    if field not in ('email_reminder', 'priority'):
        return jsonify({'success': False, 'message': f'不支持的字段: {field}'}), 400

    db = get_db()
    for pid in ids:
        db.execute(f"UPDATE patents SET {field}=?, updated_at=beijing_now() WHERE id=?",
                   (value, pid))
    db.commit()

    write_log(action='批量更新专利', module='专利管理',
              detail=f'批量更新 {len(ids)} 条专利: {field}={value}',
              user_id=g.user_id, username=g.username)

    return jsonify({'success': True, 'message': f'已更新 {len(ids)} 条专利'})


@patent_bp.route('/<int:id>', methods=['DELETE'])
@admin_required
def delete_patent(id):
    db = get_db()
    old = db.execute("SELECT * FROM patents WHERE id = ?", (id,)).fetchone()
    if not old:
        return jsonify({'success': False, 'message': '专利不存在'}), 404
    db.execute("DELETE FROM patents WHERE id = ?", (id,))
    db.commit()
    write_log(action='删除专利', module='专利管理', detail=f'删除专利「{old["name"]}」(ID={id})',
              user_id=g.user_id, username=g.username)
    return jsonify({'success': True, 'message': '专利已删除'})
