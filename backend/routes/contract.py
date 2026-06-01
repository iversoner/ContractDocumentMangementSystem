"""
合同管理 API
"""
from datetime import date, timedelta

from flask import Blueprint, request, jsonify, g

from database.db import get_db
from database.db import utc_to_beijing
from services.log_service import write_log
from middleware.auth_middleware import login_required, admin_required

contract_bp = Blueprint('contract', __name__)


def _calc_status(end_date: str) -> str:
    """根据到期日期计算状态"""
    today = date.today()
    try:
        ed = date.fromisoformat(end_date)
    except (ValueError, TypeError):
        return 'active'
    if ed < today:
        return 'expired'
    if ed <= today + timedelta(days=30):
        return 'expiring'
    return 'active'


def _row_to_dict(r) -> dict:
    return {
        'id': r['id'],
        'name': r['name'],
        'category': r['category'],
        'company': r['company'],
        'contactPerson': r['contact_person'] or '',
        'contactPhone': r['contact_phone'] or '',
        'contactEmail': r['contact_email'] or '',
        'agent': r['agent'],
        'startDate': str(r['start_date']),
        'endDate': str(r['end_date']),
        'status': r['status'],
        'filePath': r['file_path'] or '',
        'remark': r['remark'] or '',
        'createdAt': utc_to_beijing(str(r['created_at'])),
        'updatedAt': utc_to_beijing(str(r['updated_at'])),
        'source': r['source'] if 'source' in r.keys() else 'manual',
        'emailReminder': bool(r['email_reminder']) if 'email_reminder' in r.keys() else True,
        'priority': r['priority'] if 'priority' in r.keys() else '普通',
    }


@contract_bp.route('', methods=['GET'])
@login_required
def list_contracts():
    """合同列表（分页+筛选）"""
    db = get_db()
    category = request.args.get('category', '').strip()
    status = request.args.get('status', '').strip()
    keyword = request.args.get('keyword', '').strip()
    page = max(1, request.args.get('page', 1, type=int))
    page_size = max(1, min(100, request.args.get('pageSize', 10, type=int)))

    where = []
    params = []
    if category:
        where.append("category = ?")
        params.append(category)
    if status:
        where.append("status = ?")
        params.append(status)
    if keyword:
        where.append("(name LIKE ? OR company LIKE ?)")
        params.extend([f'%{keyword}%', f'%{keyword}%'])

    where_sql = (' AND '.join(where)) if where else '1=1'

    total = db.execute(f"SELECT COUNT(*) FROM contracts WHERE {where_sql}", params).fetchone()[0]
    rows = db.execute(
        f"SELECT * FROM contracts WHERE {where_sql} ORDER BY created_at DESC LIMIT ? OFFSET ?",
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


@contract_bp.route('/<int:id>', methods=['GET'])
@login_required
def get_contract(id):
    """合同详情"""
    db = get_db()
    r = db.execute("SELECT * FROM contracts WHERE id = ?", (id,)).fetchone()
    if not r:
        return jsonify({'success': False, 'message': '合同不存在'}), 404
    return jsonify({'success': True, 'data': _row_to_dict(r)})


@contract_bp.route('', methods=['POST'])
@login_required
def create_contract():
    """新增合同"""
    data = request.get_json() or {}
    required = ['name', 'category', 'company', 'agent', 'startDate', 'endDate']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'success': False, 'message': f'缺少必填字段: {", ".join(missing)}'}), 400

    status = _calc_status(data['endDate'])
    db = get_db()
    cursor = db.execute(
        """INSERT INTO contracts (name, category, company, contact_person, contact_phone,
           contact_email, agent, start_date, end_date, status, file_path, remark,
           email_reminder, priority)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (data['name'], data['category'], data['company'],
         data.get('contactPerson', ''), data.get('contactPhone', ''), data.get('contactEmail', ''),
         data['agent'], data['startDate'], data['endDate'], status,
         data.get('filePath', ''), data.get('remark', ''),
         1 if data.get('emailReminder', True) else 0,
         data.get('priority', '普通'))
    )
    db.commit()
    new_id = cursor.lastrowid
    write_log(action='新增合同', module='合同管理', detail=f'新增合同「{data["name"]}」(ID={new_id})',
              user_id=g.user_id, username=g.username)

    r = db.execute("SELECT * FROM contracts WHERE id = ?", (new_id,)).fetchone()
    return jsonify({'success': True, 'message': '合同已添加', 'data': _row_to_dict(r)}), 201


@contract_bp.route('/<int:id>', methods=['PUT'])
@login_required
def update_contract(id):
    """编辑合同"""
    db = get_db()
    old = db.execute("SELECT * FROM contracts WHERE id = ?", (id,)).fetchone()
    if not old:
        return jsonify({'success': False, 'message': '合同不存在'}), 404

    data = request.get_json() or {}
    status = _calc_status(data.get('endDate', old['end_date']))

    db.execute(
        """UPDATE contracts SET name=?, category=?, company=?, contact_person=?, contact_phone=?,
           contact_email=?, agent=?, start_date=?, end_date=?, status=?, file_path=?, remark=?,
           email_reminder=?, priority=?, updated_at=beijing_now() WHERE id=?""",
        (data.get('name', old['name']),
         data.get('category', old['category']),
         data.get('company', old['company']),
         data.get('contactPerson', old['contact_person'] or ''),
         data.get('contactPhone', old['contact_phone'] or ''),
         data.get('contactEmail', old['contact_email'] or ''),
         data.get('agent', old['agent']),
         data.get('startDate', old['start_date']),
         data.get('endDate', old['end_date']),
         status,
         data.get('filePath', old['file_path'] or ''),
         data.get('remark', old['remark'] or ''),
         1 if data.get('emailReminder', True) else 0,
         data.get('priority', old['priority'] if 'priority' in old.keys() else '普通'),
         id)
    )
    db.commit()
    write_log(action='编辑合同', module='合同管理', detail=f'编辑合同「{old["name"]}」(ID={id})',
              user_id=g.user_id, username=g.username)

    r = db.execute("SELECT * FROM contracts WHERE id = ?", (id,)).fetchone()
    return jsonify({'success': True, 'message': '合同已更新', 'data': _row_to_dict(r)})


@contract_bp.route('/batch', methods=['PUT'])
@login_required
def batch_update_contracts():
    """批量更新合同字段（邮件提醒、重要等级等）"""
    data = request.get_json() or {}
    ids = data.get('ids', [])
    field = data.get('field', '')
    value = data.get('value')

    if not ids or not field:
        return jsonify({'success': False, 'message': '缺少 ids 或 field 参数'}), 400

    if field not in ('email_reminder', 'priority'):
        return jsonify({'success': False, 'message': f'不支持的字段: {field}'}), 400

    db = get_db()
    for cid in ids:
        db.execute(f"UPDATE contracts SET {field}=?, updated_at=beijing_now() WHERE id=?",
                   (value, cid))
    db.commit()

    write_log(action='批量更新合同', module='合同管理',
              detail=f'批量更新 {len(ids)} 条合同: {field}={value}',
              user_id=g.user_id, username=g.username)

    return jsonify({'success': True, 'message': f'已更新 {len(ids)} 条合同'})


@contract_bp.route('/<int:id>', methods=['DELETE'])
@admin_required
def delete_contract(id):
    """删除合同"""
    db = get_db()
    old = db.execute("SELECT * FROM contracts WHERE id = ?", (id,)).fetchone()
    if not old:
        return jsonify({'success': False, 'message': '合同不存在'}), 404
    db.execute("DELETE FROM contracts WHERE id = ?", (id,))
    db.commit()
    write_log(action='删除合同', module='合同管理', detail=f'删除合同「{old["name"]}」(ID={id})',
              user_id=g.user_id, username=g.username)
    return jsonify({'success': True, 'message': '合同已删除'})
