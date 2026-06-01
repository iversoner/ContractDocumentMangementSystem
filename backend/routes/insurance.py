"""
车险续期管理 API
"""
from datetime import date, timedelta

from flask import Blueprint, request, jsonify, g

from database.db import get_db
from services.log_service import write_log
from middleware.auth_middleware import login_required, admin_required

insurance_bp = Blueprint('insurance', __name__)


def _calc_status(end_date: str) -> str:
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
        'plateNo': r['plate_no'],
        'brand': r['brand'],
        'insuranceCompany': r['insurance_company'],
        'insuranceType': r['insurance_type'],
        'amount': r['amount'],
        'agent': r['agent'],
        'startDate': str(r['start_date']),
        'endDate': str(r['end_date']),
        'status': r['status'],
        'filePath': r['file_path'] or '',
        'remark': r['remark'] or '',
        'createdAt': str(r['created_at']),
        'updatedAt': str(r['updated_at']),
        'source': r['source'] if 'source' in r.keys() else 'manual',
        'emailReminder': bool(r['email_reminder']) if 'email_reminder' in r.keys() else True,
        'priority': r['priority'] if 'priority' in r.keys() else '普通',
    }


@insurance_bp.route('', methods=['GET'])
@login_required
def list_insurances():
    db = get_db()
    status = request.args.get('status', '').strip()
    company = request.args.get('company', '').strip()
    keyword = request.args.get('keyword', '').strip()
    page = max(1, request.args.get('page', 1, type=int))
    page_size = max(1, min(100, request.args.get('pageSize', 10, type=int)))

    where = []
    params = []
    if status:
        where.append("status = ?")
        params.append(status)
    if company:
        where.append("insurance_company = ?")
        params.append(company)
    if keyword:
        where.append("(plate_no LIKE ? OR brand LIKE ?)")
        params.extend([f'%{keyword}%', f'%{keyword}%'])

    where_sql = (' AND '.join(where)) if where else '1=1'

    total = db.execute(f"SELECT COUNT(*) FROM insurances WHERE {where_sql}", params).fetchone()[0]
    rows = db.execute(
        f"SELECT * FROM insurances WHERE {where_sql} ORDER BY created_at DESC LIMIT ? OFFSET ?",
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


@insurance_bp.route('/stats', methods=['GET'])
@login_required
def insurance_stats():
    """车险统计：总数、生效中、即将到期、已过期"""
    db = get_db()
    total = db.execute("SELECT COUNT(*) FROM insurances").fetchone()[0]
    active = db.execute("SELECT COUNT(*) FROM insurances WHERE status='active'").fetchone()[0]
    expiring = db.execute("SELECT COUNT(*) FROM insurances WHERE status='expiring'").fetchone()[0]
    expired = db.execute("SELECT COUNT(*) FROM insurances WHERE status='expired'").fetchone()[0]
    return jsonify({
        'success': True,
        'data': {
            'total': total,
            'active': active,
            'expiring': expiring,
            'expired': expired,
        }
    })


@insurance_bp.route('/<int:id>', methods=['GET'])
@login_required
def get_insurance(id):
    db = get_db()
    r = db.execute("SELECT * FROM insurances WHERE id = ?", (id,)).fetchone()
    if not r:
        return jsonify({'success': False, 'message': '车险记录不存在'}), 404
    return jsonify({'success': True, 'data': _row_to_dict(r)})


@insurance_bp.route('', methods=['POST'])
@login_required
def create_insurance():
    data = request.get_json() or {}
    required = ['plateNo', 'brand', 'insuranceCompany', 'insuranceType', 'agent', 'startDate', 'endDate']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'success': False, 'message': f'缺少必填字段: {", ".join(missing)}'}), 400

    status = _calc_status(data['endDate'])
    db = get_db()
    cursor = db.execute(
        """INSERT INTO insurances (plate_no, brand, insurance_company, insurance_type,
           amount, agent, start_date, end_date, status, file_path, remark,
           email_reminder, priority)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (data['plateNo'], data['brand'], data['insuranceCompany'], data['insuranceType'],
         data.get('amount', 0), data['agent'], data['startDate'], data['endDate'], status,
         data.get('filePath', ''), data.get('remark', ''),
         1 if data.get('emailReminder', True) else 0,
         data.get('priority', '普通'))
    )
    db.commit()
    new_id = cursor.lastrowid
    write_log(action='新增车险', module='车险续期', detail=f'新增车险「{data["plateNo"]} {data["brand"]}」(ID={new_id})',
              user_id=g.user_id, username=g.username)

    r = db.execute("SELECT * FROM insurances WHERE id = ?", (new_id,)).fetchone()
    return jsonify({'success': True, 'message': '车险记录已添加', 'data': _row_to_dict(r)}), 201


@insurance_bp.route('/<int:id>', methods=['PUT'])
@login_required
def update_insurance(id):
    db = get_db()
    old = db.execute("SELECT * FROM insurances WHERE id = ?", (id,)).fetchone()
    if not old:
        return jsonify({'success': False, 'message': '车险记录不存在'}), 404

    data = request.get_json() or {}
    status = _calc_status(data.get('endDate', old['end_date']))

    db.execute(
        """UPDATE insurances SET plate_no=?, brand=?, insurance_company=?, insurance_type=?,
           amount=?, agent=?, start_date=?, end_date=?, status=?, file_path=?, remark=?,
           email_reminder=?, priority=?, updated_at=CURRENT_TIMESTAMP WHERE id=?""",
        (data.get('plateNo', old['plate_no']),
         data.get('brand', old['brand']),
         data.get('insuranceCompany', old['insurance_company']),
         data.get('insuranceType', old['insurance_type']),
         data.get('amount', old['amount']),
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
    write_log(action='编辑车险', module='车险续期', detail=f'编辑车险「{old["plate_no"]} {old["brand"]}」(ID={id})',
              user_id=g.user_id, username=g.username)

    r = db.execute("SELECT * FROM insurances WHERE id = ?", (id,)).fetchone()
    return jsonify({'success': True, 'message': '车险记录已更新', 'data': _row_to_dict(r)})


@insurance_bp.route('/batch', methods=['PUT'])
@login_required
def batch_update_insurances():
    """批量更新车险字段"""
    data = request.get_json() or {}
    ids = data.get('ids', [])
    field = data.get('field', '')
    value = data.get('value')

    if not ids or not field:
        return jsonify({'success': False, 'message': '缺少 ids 或 field 参数'}), 400

    if field not in ('email_reminder', 'priority'):
        return jsonify({'success': False, 'message': f'不支持的字段: {field}'}), 400

    db = get_db()
    for iid in ids:
        db.execute(f"UPDATE insurances SET {field}=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                   (value, iid))
    db.commit()

    write_log(action='批量更新车险', module='车险续期',
              detail=f'批量更新 {len(ids)} 条车险: {field}={value}',
              user_id=g.user_id, username=g.username)

    return jsonify({'success': True, 'message': f'已更新 {len(ids)} 条车险'})


@insurance_bp.route('/<int:id>', methods=['DELETE'])
@admin_required
def delete_insurance(id):
    db = get_db()
    old = db.execute("SELECT * FROM insurances WHERE id = ?", (id,)).fetchone()
    if not old:
        return jsonify({'success': False, 'message': '车险记录不存在'}), 404
    db.execute("DELETE FROM insurances WHERE id = ?", (id,))
    db.commit()
    write_log(action='删除车险', module='车险续期', detail=f'删除车险「{old["plate_no"]} {old["brand"]}」(ID={id})',
              user_id=g.user_id, username=g.username)
    return jsonify({'success': True, 'message': '车险记录已删除'})
