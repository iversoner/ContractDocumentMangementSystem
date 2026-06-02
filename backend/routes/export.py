"""
数据导出 API — 生成 .xlsx 文件保存到 /data/exports/
"""
import os

from flask import Blueprint, request, jsonify, g

from database.db import get_db, beijing_now
from services.log_service import write_log
from middleware.auth_middleware import login_required

export_bp = Blueprint('export', __name__)

# 导出文件保存目录（Docker 内为 /data/exports/，本地开发为 backend/exports/）
def _export_dir():
    import flask
    db_path = flask.current_app.config.get('DATABASE_PATH', 'backend/database/suzhen.db')
    if db_path.startswith('/data/'):
        return '/data/exports'
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'exports')


@export_bp.route('', methods=['POST'])
@login_required
def export_data():
    data = request.get_json() or {}
    export_type = data.get('type', 'all')
    format_type = data.get('format', 'json')

    db = get_db()

    # 构建查询
    def _query(table, create_filter='', exp_filter=''):
        if export_type == 'byCreate' and create_filter:
            return [dict(r) for r in db.execute(f"SELECT * FROM {table} {create_filter}", _params('create')).fetchall()]
        if export_type == 'byExpire' and exp_filter:
            return [dict(r) for r in db.execute(f"SELECT * FROM {table} {exp_filter}", _params('expire')).fetchall()]
        return [dict(r) for r in db.execute(f"SELECT * FROM {table}").fetchall()]

    def _params(kind):
        if kind == 'create':
            return [data.get('startDate', '') + ' 00:00:00', data.get('endDate', '') + ' 23:59:59']
        return [data.get('startDate', ''), data.get('endDate', '')]

    # 校验
    if export_type in ('byCreate', 'byExpire'):
        if not data.get('startDate') or not data.get('endDate'):
            return jsonify({'success': False, 'message': '请选择时间范围'}), 400

    create_where = "WHERE created_at >= ? AND created_at <= ?" if export_type == 'byCreate' else ''
    expire_contract = "WHERE end_date >= ? AND end_date <= ?" if export_type == 'byExpire' else ''
    expire_patent = "WHERE expire_date >= ? AND expire_date <= ?" if export_type == 'byExpire' else ''
    expire_insurance = "WHERE end_date >= ? AND end_date <= ?" if export_type == 'byExpire' else ''

    contracts = _query('contracts', create_where, expire_contract)
    patents = _query('patents', create_where, expire_patent)
    insurances = _query('insurances', create_where, expire_insurance)

    # JSON 导出（保留兼容）
    if format_type == 'json':
        result = {
            'contracts': contracts,
            'patents': patents,
            'insurances': insurances,
            'exportInfo': {
                'type': export_type,
                'exportedAt': beijing_now(),
                'exporter': g.username,
                'totalContracts': len(contracts),
                'totalPatents': len(patents),
                'totalInsurances': len(insurances),
            }
        }
        write_log(action='导出数据', module='数据导出',
                  detail=f'JSON导出: 合同{len(contracts)}条, 专利{len(patents)}条, 车险{len(insurances)}条',
                  user_id=g.user_id, username=g.username)
        return jsonify({'success': True, 'data': result})

    # Excel (.xlsx) 导出
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    except ImportError:
        return jsonify({'success': False, 'message': '服务器未安装 openpyxl，请联系管理员'}), 500

    wb = Workbook()
    # 删除默认 sheet
    wb.remove(wb.active)

    header_font = Font(name='微软雅黑', bold=True, size=11, color='FFFFFF')
    header_fill = PatternFill(start_color='4472C4', end_color='4472C4', fill_type='solid')
    header_align = Alignment(horizontal='center', vertical='center')
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'),
        top=Side(style='thin'), bottom=Side(style='thin')
    )

    def _write_sheet(ws, rows, title):
        if not rows:
            ws.append([f'{title}：无数据'])
            return
        # 写表头
        headers = list(rows[0].keys())
        for col_idx, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=h)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_align
            cell.border = thin_border
        # 写数据
        for row_idx, row in enumerate(rows, 2):
            for col_idx, h in enumerate(headers, 1):
                val = row.get(h, '')
                if val is None:
                    val = ''
                cell = ws.cell(row=row_idx, column=col_idx, value=val)
                cell.border = thin_border
        # 自动列宽
        for col_idx, h in enumerate(headers, 1):
            max_len = len(str(h))
            for row_idx in range(2, len(rows) + 2):
                val = ws.cell(row=row_idx, column=col_idx).value
                if val:
                    max_len = max(max_len, len(str(val)))
            ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = min(max_len + 4, 40)

    ws1 = wb.create_sheet('合同数据')
    _write_sheet(ws1, contracts, '合同数据')
    ws2 = wb.create_sheet('专利数据')
    _write_sheet(ws2, patents, '专利数据')
    ws3 = wb.create_sheet('车险数据')
    _write_sheet(ws3, insurances, '车险数据')

    # 保存文件
    export_dir = _export_dir()
    os.makedirs(export_dir, exist_ok=True)
    timestamp = beijing_now().replace(':', '-').replace(' ', '_')
    filename = f'export_{timestamp}.xlsx'
    filepath = os.path.join(export_dir, filename)
    wb.save(filepath)

    write_log(action='导出数据', module='数据导出',
              detail=f'Excel导出: {filename} (合同{len(contracts)}条, 专利{len(patents)}条, 车险{len(insurances)}条)',
              user_id=g.user_id, username=g.username)

    return jsonify({
        'success': True,
        'data': {
            'filename': filename,
            'filepath': filepath,
            'exportInfo': {
                'type': export_type,
                'exportedAt': beijing_now(),
                'exporter': g.username,
                'totalContracts': len(contracts),
                'totalPatents': len(patents),
                'totalInsurances': len(insurances),
            }
        },
        'message': f'导出成功！文件已保存: {filepath}'
    })
