"""
数据导出 API
"""
import csv
import io
import json

from flask import Blueprint, request, jsonify, Response, g

from database.db import get_db
from services.log_service import write_log
from middleware.auth_middleware import login_required

export_bp = Blueprint('export', __name__)


@export_bp.route('', methods=['POST'])
@login_required
def export_data():
    data = request.get_json() or {}
    export_type = data.get('type', 'all')
    format_type = data.get('format', 'json')

    db = get_db()
    contracts = []
    patents = []
    insurances = []

    # 构建时间过滤条件
    if export_type == 'byCreate':
        start = data.get('startDate', '')
        end = data.get('endDate', '')
        if not start or not end:
            return jsonify({'success': False, 'message': '请选择创建时间范围'}), 400
        create_filter = "WHERE created_at >= ? AND created_at <= ?"
        create_params = [start + ' 00:00:00', end + ' 23:59:59']
    elif export_type == 'byExpire':
        start = data.get('startDate', '')
        end = data.get('endDate', '')
        if not start or not end:
            return jsonify({'success': False, 'message': '请选择到期时间范围'}), 400
        contract_filter = "WHERE end_date >= ? AND end_date <= ?"
        patent_filter = "WHERE expire_date >= ? AND expire_date <= ?"
        insurance_filter = "WHERE end_date >= ? AND end_date <= ?"
        exp_params = [start, end]
        contracts = [dict(r) for r in db.execute(f"SELECT * FROM contracts {contract_filter}", exp_params).fetchall()]
        patents = [dict(r) for r in db.execute(f"SELECT * FROM patents {patent_filter}", exp_params).fetchall()]
        insurances = [dict(r) for r in db.execute(f"SELECT * FROM insurances {insurance_filter}", exp_params).fetchall()]
    else:
        # all
        contracts = [dict(r) for r in db.execute("SELECT * FROM contracts").fetchall()]
        patents = [dict(r) for r in db.execute("SELECT * FROM patents").fetchall()]
        insurances = [dict(r) for r in db.execute("SELECT * FROM insurances").fetchall()]

    # 按创建时间导出
    if export_type == 'byCreate':
        contracts = [dict(r) for r in db.execute(f"SELECT * FROM contracts {create_filter}", create_params).fetchall()]
        patents = [dict(r) for r in db.execute(f"SELECT * FROM patents {create_filter}", create_params).fetchall()]
        insurances = [dict(r) for r in db.execute(f"SELECT * FROM insurances {create_filter}", create_params).fetchall()]

    result = {
        'contracts': contracts,
        'patents': patents,
        'insurances': insurances,
        'exportInfo': {
            'type': export_type,
            'exportedAt': db.execute("SELECT datetime('now')").fetchone()[0],
            'exporter': g.username,
            'totalContracts': len(contracts),
            'totalPatents': len(patents),
            'totalInsurances': len(insurances),
        }
    }

    write_log(action='导出数据', module='数据导出',
              detail=f'导出数据: 合同{len(contracts)}条, 专利{len(patents)}条, 车险{len(insurances)}条',
              user_id=g.user_id, username=g.username)

    if format_type == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        # CSV 导出所有合同
        writer.writerow(['=== 合同数据 ==='])
        if contracts:
            writer.writerow(contracts[0].keys())
            for c in contracts:
                writer.writerow(c.values())
        writer.writerow([])
        writer.writerow(['=== 专利数据 ==='])
        if patents:
            writer.writerow(patents[0].keys())
            for p in patents:
                writer.writerow(p.values())
        writer.writerow([])
        writer.writerow(['=== 车险数据 ==='])
        if insurances:
            writer.writerow(insurances[0].keys())
            for i in insurances:
                writer.writerow(i.values())

        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=export.csv'}
        )

    return jsonify({'success': True, 'data': result})
