"""
仪表盘接口：统计数据、最近项目、即将到期
"""
from flask import Blueprint, jsonify

from database.db import get_db
from middleware.auth_middleware import login_required

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/stats', methods=['GET'])
@login_required
def stats():
    """仪表盘统计数据"""
    db = get_db()
    today = db.execute("SELECT date('now')").fetchone()[0]
    thirty_days_later = db.execute("SELECT date('now', '+30 days')").fetchone()[0]

    # 各表统计
    total_contracts = db.execute("SELECT COUNT(*) FROM contracts").fetchone()[0]
    active_contracts = db.execute("SELECT COUNT(*) FROM contracts WHERE status='active'").fetchone()[0]
    total_patents = db.execute("SELECT COUNT(*) FROM patents").fetchone()[0]
    total_insurances = db.execute("SELECT COUNT(*) FROM insurances").fetchone()[0]
    total_files = db.execute("SELECT COUNT(*) FROM files").fetchone()[0]
    total_users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]

    # 即将到期：合同中即将到期
    expiring_contracts = db.execute(
        "SELECT COUNT(*) FROM contracts WHERE status='expiring' "
        "OR (end_date >= ? AND end_date <= ? AND status != 'expired')",
        (today, thirty_days_later)
    ).fetchone()[0]

    # 即将到期：保险中即将到期
    expiring_insurances = db.execute(
        "SELECT COUNT(*) FROM insurances WHERE status='expiring' "
        "OR (end_date >= ? AND end_date <= ? AND status != 'expired')",
        (today, thirty_days_later)
    ).fetchone()[0]

    # 已到期
    expired_contracts = db.execute("SELECT COUNT(*) FROM contracts WHERE status='expired' OR end_date < ?",
                                   (today,)).fetchone()[0]
    expired_insurances = db.execute("SELECT COUNT(*) FROM insurances WHERE status='expired' OR end_date < ?",
                                    (today,)).fetchone()[0]
    expired_patents = db.execute("SELECT COUNT(*) FROM patents WHERE status='expired' OR expire_date < ?",
                                 (today,)).fetchone()[0]

    return jsonify({
        'success': True,
        'data': {
            'totalContracts': total_contracts,
            'activeContracts': active_contracts,
            'totalPatents': total_patents,
            'totalInsurances': total_insurances,
            'totalFiles': total_files,
            'totalUsers': total_users,
            'expiringSoon': expiring_contracts + expiring_insurances,
            'expired': expired_contracts + expired_insurances + expired_patents,
        }
    })


@dashboard_bp.route('/recent', methods=['GET'])
@login_required
def recent():
    """最近添加的项目（合并所有类型，取前10条）"""
    db = get_db()
    rows = db.execute("""
        SELECT name, '合同' AS type, created_at FROM contracts
        UNION ALL
        SELECT name, '专利' AS type, created_at FROM patents
        UNION ALL
        SELECT plate_no || ' ' || brand AS name, '车险' AS type, created_at FROM insurances
        ORDER BY created_at DESC LIMIT 10
    """).fetchall()

    items = [{'name': r['name'], 'type': r['type'], 'createdAt': str(r['created_at'])} for r in rows]
    return jsonify({'success': True, 'data': items})


@dashboard_bp.route('/expiring', methods=['GET'])
@login_required
def expiring():
    """即将到期项目（30天内）"""
    db = get_db()
    today = db.execute("SELECT date('now')").fetchone()[0]
    thirty_days = db.execute("SELECT date('now', '+30 days')").fetchone()[0]

    contracts = db.execute("""
        SELECT name, company, contact_person, start_date, end_date, priority, '合同' AS type, status
        FROM contracts
        WHERE end_date >= ? AND end_date <= ? AND status != 'expired' AND email_reminder = 1
        ORDER BY end_date ASC
    """, (today, thirty_days)).fetchall()

    patents = db.execute("""
        SELECT name, holder, application_date, expire_date, priority, '专利' AS type, status
        FROM patents
        WHERE expire_date >= ? AND expire_date <= ? AND status != 'expired' AND email_reminder = 1
        ORDER BY expire_date ASC
    """, (today, thirty_days)).fetchall()

    insurances = db.execute("""
        SELECT plate_no || ' ' || brand AS name, insurance_company, start_date, end_date, priority,
               '车险' AS type, status
        FROM insurances
        WHERE end_date >= ? AND end_date <= ? AND status != 'expired' AND email_reminder = 1
        ORDER BY end_date ASC
    """, (today, thirty_days)).fetchall()

    items = []
    for r in contracts:
        items.append({
            'name': r['name'],
            'type': r['type'],
            'company': r['company'],
            'contactPerson': r['contact_person'],
            'startDate': str(r['start_date']),
            'endDate': str(r['end_date']),
            'status': r['status'],
            'priority': r['priority'] or '普通',
        })
    for r in patents:
        items.append({
            'name': r['name'],
            'type': r['type'],
            'company': r['holder'],
            'contactPerson': '',
            'startDate': str(r['application_date']),
            'endDate': str(r['expire_date']),
            'status': r['status'],
            'priority': r['priority'] or '普通',
        })
    for r in insurances:
        items.append({
            'name': r['name'],
            'type': r['type'],
            'company': r['insurance_company'],
            'contactPerson': '',
            'startDate': str(r['start_date']),
            'endDate': str(r['end_date']),
            'status': r['status'],
            'priority': r['priority'] or '普通',
        })

    return jsonify({'success': True, 'data': items})
